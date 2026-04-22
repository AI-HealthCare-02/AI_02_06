"""Hybrid retriever combining pgvector similarity and keyword matching.

Queries `medicine_chunk` for dense embedding similarity (pgvector cosine),
joins parent `medicine_info` rows, groups chunks under their parent
medicine, and combines the top-1 chunk score with a keyword-overlap score
against `medicine_name + category` for final ranking.
"""

import logging
import re

from tortoise import connections

from app.dtos.rag import ChunkMatch, SearchFilters, SearchResult
from app.models.medicine_chunk import MedicineChunk
from app.models.medicine_info import MedicineInfo
from app.services.rag.protocols import EmbeddingProvider

logger = logging.getLogger(__name__)

_STOP_WORDS: frozenset[str] = frozenset({
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "에서",
    "로",
    "으로",
    "와",
    "과",
    "하고",
})


class HybridRetriever:
    """Retriever combining pgvector similarity with keyword scoring.

    Weights are normalized so vector_weight + keyword_weight == 1.0.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        """Initialize hybrid retriever.

        Args:
            embedding_provider: Provider used for query embedding.
            vector_weight: Weight for vector similarity score.
            keyword_weight: Weight for keyword matching score.
        """
        self.embedding_provider = embedding_provider
        total = vector_weight + keyword_weight
        self.vector_weight = vector_weight / total
        self.keyword_weight = keyword_weight / total

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        filters: SearchFilters,
        limit: int,
    ) -> list[SearchResult]:
        """Retrieve ranked medicine results for a query.

        Args:
            query: Original query text for keyword scoring.
            query_embedding: Pre-computed query embedding vector.
            filters: Metadata filters to apply.
            limit: Maximum number of SearchResult entries to return.

        Returns:
            SearchResult list sorted by final_score descending. Each result
            carries its parent MedicineInfo plus every chunk that surfaced
            for that medicine (in matched_chunks).
        """
        vector_results = await self._vector_search(query_embedding, filters, limit * 3)
        if not vector_results:
            return []

        query_keywords = self.extract_keywords(query)
        results: list[SearchResult] = []

        for medicine, chunk_matches in vector_results:
            top_chunk_score = chunk_matches[0].vector_score if chunk_matches else 0.0
            keyword_score = self.calculate_keyword_score(
                query_keywords=query_keywords,
                medicine_name=medicine.medicine_name,
                category=medicine.category,
            )
            final_score = self.vector_weight * top_chunk_score + self.keyword_weight * keyword_score
            results.append(
                SearchResult(
                    medicine=medicine,
                    matched_chunks=chunk_matches,
                    vector_score=top_chunk_score,
                    keyword_score=keyword_score,
                    final_score=final_score,
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:limit]

    async def _vector_search(
        self,
        query_embedding: list[float],
        filters: SearchFilters,
        limit: int,
        similarity_threshold: float = 0.5,
    ) -> list[tuple[MedicineInfo, list[ChunkMatch]]]:
        """Run pgvector cosine search on medicine_chunk and group by parent.

        Args:
            query_embedding: Query vector.
            filters: Metadata filters (applied against medicine_info).
            limit: Maximum chunk candidates to fetch before grouping.
            similarity_threshold: Minimum cosine similarity (0..1).

        Returns:
            List of (MedicineInfo, list[ChunkMatch]) tuples. Each medicine
            appears once and its chunks are sorted by vector_score desc.
            The outer list is ordered by each medicine's top-1 chunk score.
        """
        connection = connections.get("default")
        vector_str = f"[{','.join(map(str, query_embedding))}]"

        where_conditions: list[str] = ["(mc.embedding <=> $1) < $2"]
        params: list = [vector_str, 1 - similarity_threshold]
        idx = 3

        if filters.medicine_names:
            where_conditions.append(f"mi.medicine_name = ANY(${idx})")
            params.append(filters.medicine_names)
            idx += 1

        where_clause = " AND ".join(where_conditions)
        sql = f"""
        SELECT
            mc.id AS chunk_id,
            mc.medicine_info_id,
            mc.section,
            mc.chunk_index,
            mc.content,
            mc.token_count,
            mc.model_version,
            mc.created_at AS chunk_created_at,
            mc.updated_at AS chunk_updated_at,
            (mc.embedding <=> $1) AS distance,
            mi.id AS mi_id,
            mi.item_seq,
            mi.medicine_name,
            mi.item_eng_name,
            mi.entp_name,
            mi.category,
            mi.efficacy,
            mi.side_effects,
            mi.precautions,
            mi.atc_code,
            mi.ee_doc_url,
            mi.ud_doc_url,
            mi.nb_doc_url
        FROM medicine_chunk mc
        INNER JOIN medicine_info mi ON mi.id = mc.medicine_info_id
        WHERE {where_clause}
        ORDER BY distance ASC
        LIMIT ${idx}
        """  # noqa: S608
        params.append(limit)

        rows = await connection.execute_query_dict(sql, params)
        logger.info("[RAG] pgvector(chunk): %d rows (threshold=%.2f)", len(rows), similarity_threshold)

        # Build raw hits preserving order (already sorted by distance asc)
        raw_hits: list[tuple[MedicineInfo, MedicineChunk, float]] = []
        for row in rows:
            distance = row["distance"]
            vector_score = 1 - distance
            medicine = MedicineInfo(
                id=row["mi_id"],
                item_seq=row["item_seq"],
                medicine_name=row["medicine_name"],
                item_eng_name=row["item_eng_name"],
                entp_name=row["entp_name"],
                category=row["category"],
                efficacy=row["efficacy"],
                side_effects=row["side_effects"],
                precautions=row["precautions"],
                atc_code=row["atc_code"],
                ee_doc_url=row["ee_doc_url"],
                ud_doc_url=row["ud_doc_url"],
                nb_doc_url=row["nb_doc_url"],
            )
            chunk = MedicineChunk(
                id=row["chunk_id"],
                medicine_info_id=row["medicine_info_id"],
                section=row["section"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                token_count=row["token_count"],
                model_version=row["model_version"],
            )
            raw_hits.append((medicine, chunk, vector_score))

        return self._group_chunks_by_medicine(raw_hits)

    def _group_chunks_by_medicine(
        self,
        raw_hits: list[tuple[MedicineInfo, MedicineChunk, float]],
    ) -> list[tuple[MedicineInfo, list[ChunkMatch]]]:
        """Group chunk-level hits under their parent medicine.

        Order is preserved: the first group is the medicine whose top-1
        chunk appeared first in `raw_hits`. Within each group, ChunkMatch
        entries keep the input order (already sorted by vector_score desc).
        """
        grouped: dict[int, tuple[MedicineInfo, list[ChunkMatch]]] = {}
        order: list[int] = []
        for medicine, chunk, vector_score in raw_hits:
            mid = medicine.id
            if mid not in grouped:
                grouped[mid] = (medicine, [])
                order.append(mid)
            grouped[mid][1].append(ChunkMatch(chunk=chunk, vector_score=vector_score))
        return [grouped[mid] for mid in order]

    def calculate_keyword_score(
        self,
        query_keywords: list[str],
        medicine_name: str,
        category: str | None,
    ) -> float:
        """Keyword overlap score against medicine_name + category.

        Name hits count twice as much as category hits. Returns 0.0 when
        no query keywords, and is bounded to [0.0, 1.0].

        Args:
            query_keywords: Keywords extracted from the user query.
            medicine_name: Parent medicine's medicine_name.
            category: Parent medicine's category (nullable on the main schema).

        Returns:
            Score in [0.0, 1.0].
        """
        if not query_keywords:
            return 0.0

        name_lower = medicine_name.lower()
        category_lower = (category or "").lower()
        matches = 0
        for keyword in query_keywords:
            kw_lower = keyword.lower()
            if kw_lower in name_lower:
                matches += 2  # Name hits weighted higher
            if category_lower and kw_lower in category_lower:
                matches += 1

        max_possible = len(query_keywords) * 3
        return min(matches / max_possible, 1.0)

    def extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful Korean/alphanumeric keywords from a query.

        Strips trailing Korean particles (은/는/이/가/을/를 ...) so that
        '타이레놀의' reduces to '타이레놀' before lexical matching.

        Args:
            query: User query string.

        Returns:
            Keyword list with stopwords and single-char tokens removed.
        """
        words = re.findall(r"[가-힣a-zA-Z0-9]+", query)
        keywords: list[str] = []
        for raw in words:
            if raw.lower() in _STOP_WORDS or len(raw) <= 1:
                continue
            keywords.append(self._strip_trailing_particle(raw))
        return keywords

    def _strip_trailing_particle(self, word: str) -> str:
        """Remove a known particle suffix when the stem would remain >= 2 chars."""
        for particle in _STOP_WORDS:
            if word.endswith(particle) and len(word) - len(particle) >= 2:
                return word[: -len(particle)]
        return word
