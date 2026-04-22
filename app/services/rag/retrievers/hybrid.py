"""Hybrid retriever combining pgvector similarity and keyword matching.

Queries the `medicine_info` table using pgvector cosine distance for the
vector leg and a bounded keyword-overlap score over the medicine's name
and concatenated text fields for the lexical leg. Final score is a
convex combination of the two.
"""

import logging
import re

from tortoise import connections

from app.dtos.rag import SearchFilters, SearchResult
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
        """Retrieve ranked MedicineInfo matches for a query.

        Args:
            query: Original query text for keyword scoring.
            query_embedding: Pre-computed query embedding vector.
            filters: Metadata filters to apply.
            limit: Maximum number of results.

        Returns:
            SearchResult list sorted by final_score descending.
        """
        vector_results = await self._vector_search(query_embedding, filters, limit * 3)

        if not vector_results:
            return []

        query_keywords = self._extract_keywords(query)
        results: list[SearchResult] = []

        for medicine, vector_score in vector_results:
            keyword_score = self.calculate_keyword_score(
                query_keywords=query_keywords,
                medicine_text=self._build_medicine_text(medicine),
                medicine_name=medicine.name,
            )
            final_score = self.vector_weight * vector_score + self.keyword_weight * keyword_score
            results.append(
                SearchResult(
                    medicine=medicine,
                    vector_score=vector_score,
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
    ) -> list[tuple[MedicineInfo, float]]:
        """Perform pgvector cosine similarity search on medicine_info.

        Args:
            query_embedding: Query vector.
            filters: Metadata filters.
            limit: Maximum candidates.
            similarity_threshold: Minimum cosine similarity (0..1).

        Returns:
            List of (MedicineInfo, similarity_score) tuples.
        """
        connection = connections.get("default")
        vector_str = f"[{','.join(map(str, query_embedding))}]"

        where_conditions: list[str] = ["(embedding <=> $1) < $2"]
        params: list = [vector_str, 1 - similarity_threshold]
        idx = 3

        if filters.medicine_names:
            where_conditions.append(f"name = ANY(${idx})")
            params.append(filters.medicine_names)
            idx += 1

        where_clause = " AND ".join(where_conditions)
        sql = f"""
        SELECT mi.*, (mi.embedding <=> $1) as distance
        FROM medicine_info mi
        WHERE {where_clause}
        ORDER BY distance ASC
        LIMIT ${idx}
        """  # noqa: S608
        params.append(limit)

        rows = await connection.execute_query_dict(sql, params)
        logger.info("[RAG] pgvector: %d rows (threshold=%.2f)", len(rows), similarity_threshold)
        results: list[tuple[MedicineInfo, float]] = []
        for row in rows:
            distance = row.pop("distance")
            results.append((MedicineInfo(**row), 1 - distance))
        return results

    def calculate_keyword_score(
        self,
        query_keywords: list[str],
        medicine_text: str,
        medicine_name: str,
    ) -> float:
        """Keyword overlap score between query and a medicine row.

        A match on `medicine_name` weighs more than a match inside
        `medicine_text` (concatenated ingredient/usage/disclaimer/...).

        Args:
            query_keywords: Keywords extracted from the query.
            medicine_text: Concatenated searchable text of the medicine.
            medicine_name: Medicine's canonical name.

        Returns:
            Score in [0.0, 1.0].
        """
        if not query_keywords:
            return 0.0

        text_lower = medicine_text.lower()
        name_lower = medicine_name.lower()
        matches = 0

        for keyword in query_keywords:
            kw_lower = keyword.lower()
            if kw_lower in name_lower:
                matches += 2  # Name hits are weighted higher
            if kw_lower in text_lower:
                matches += 1

        max_possible = len(query_keywords) * 3
        return min(matches / max_possible, 1.0)

    def _extract_keywords(self, query: str) -> list[str]:
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

    def _build_medicine_text(self, medicine: MedicineInfo) -> str:
        """Concatenate searchable medicine fields for keyword scoring.

        Args:
            medicine: MedicineInfo row.

        Returns:
            Space-joined text of ingredient, usage, disclaimer, and
            contraindicated lists.
        """
        parts: list[str] = [
            medicine.ingredient or "",
            medicine.usage or "",
            medicine.disclaimer or "",
        ]
        parts.extend(medicine.contraindicated_drugs or [])
        parts.extend(medicine.contraindicated_foods or [])
        return " ".join(p for p in parts if p)
