"""Hybrid retriever — pgvector cosine + tsvector BM25 RRF 융합.

PLAN.md (feature/RAG) §3 C2 결정:
- 1차 RRF (intra-query): vector rank ↔ BM25 rank 병합 (Cormack k=60)
- 가중합 (vector_weight 0.7 + keyword 0.3) 폐기 → RRF 표준 알고리즘 사용
- tsvector 검색은 28번 마이그의 content_tsv 컬럼 + GIN 인덱스 활용
"""

import logging
import re

from tortoise import connections

from app.dtos.rag import ChunkMatch, SearchFilters, SearchResult
from app.models.medicine_chunk import MedicineChunk
from app.models.medicine_info import MedicineInfo
from app.services.rag.protocols import EmbeddingProvider
from app.services.rag.retrievers.rrf import rrf_intra_query

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
    """Retriever — pgvector cosine + tsvector BM25 RRF 융합.

    PLAN.md (feature/RAG) §3 C2 — Cormack et al. 2009 표준 RRF (k=60).
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        """Initialize hybrid retriever.

        Args:
            embedding_provider: Provider used for query embedding (인터페이스만,
                실 query 임베딩은 caller 가 사전 계산하여 ``query_embedding``
                인자로 넘김).
        """
        self.embedding_provider = embedding_provider

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        filters: SearchFilters,
        limit: int,
    ) -> list[SearchResult]:
        """Retrieve ranked medicine results for a query (1차 RRF).

        Args:
            query: Original query text — tsvector 검색 입력으로 사용.
            query_embedding: Pre-computed query embedding vector.
            filters: Metadata filters to apply.
            limit: Maximum number of SearchResult entries to return.

        Returns:
            SearchResult list — RRF score 내림차순 + limit 개. 각 result 의
            ``vector_score``/``keyword_score`` 는 raw 값, ``final_score`` 는
            RRF score.
        """
        # 후보군 — vector / bm25 각각 limit*3 개 회수 후 RRF 로 줄임
        candidate_limit = limit * 3
        vector_groups = await self._vector_search(query_embedding, filters, candidate_limit)
        bm25_groups = await self._bm25_search(query, filters, candidate_limit)

        if not vector_groups and not bm25_groups:
            return []

        # 1차 RRF — chunk_id 기준 vector + bm25 rank 병합
        vector_hits = [
            {"chunk_id": cm.chunk.id, "medicine": med, "match": cm} for med, matches in vector_groups for cm in matches
        ]
        bm25_hits = [
            {"chunk_id": cm.chunk.id, "medicine": med, "match": cm} for med, matches in bm25_groups for cm in matches
        ]
        merged = rrf_intra_query(vector_hits, bm25_hits)
        logger.info(
            "[RAG] RRF intra-query merged %d unique chunks (vec=%d bm25=%d)",
            len(merged),
            len(vector_hits),
            len(bm25_hits),
        )

        # medicine 단위 grouping (RRF score 합산)
        return self._group_by_medicine(merged, limit)

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
        sql, params = self._build_vector_search_sql(query_embedding, filters, similarity_threshold, limit)
        rows = await connections.get("default").execute_query_dict(sql, params)
        logger.info("[RAG] pgvector(chunk): %d rows (threshold=%.2f)", len(rows), similarity_threshold)
        raw_hits = [self._row_to_hit(row) for row in rows]
        return self._group_chunks_by_medicine(raw_hits)

    @staticmethod
    def _build_vector_search_sql(
        query_embedding: list[float],
        filters: SearchFilters,
        similarity_threshold: float,
        limit: int,
    ) -> tuple[str, list]:
        """Build the SQL + params for the chunk-level pgvector search.

        Args:
            query_embedding: Query vector.
            filters: Metadata filters.
            similarity_threshold: Minimum cosine similarity (0..1).
            limit: Max rows to fetch.

        Returns:
            ``(sql, params)`` ready for ``connection.execute_query_dict``.
        """
        vector_str = f"[{','.join(map(str, query_embedding))}]"
        where_conditions: list[str] = ["(mc.embedding <=> $1) < $2"]
        params: list = [vector_str, 1 - similarity_threshold]
        idx = 3
        if filters.medicine_names:
            where_conditions.append(f"mi.medicine_name = ANY(${idx})")
            params.append(filters.medicine_names)
            idx += 1
        where_clause = " AND ".join(where_conditions)
        # where_conditions 의 모든 element 는 코드 내부 상수 + 값은 $N 바인딩 → SQL injection 안전.
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
        """  # noqa: S608  # nosec B608
        params.append(limit)
        return sql, params

    @staticmethod
    def _row_to_hit(row: dict) -> tuple[MedicineInfo, MedicineChunk, float]:
        """Map one SQL row to ``(medicine, chunk, vector_score)``."""
        vector_score = 1 - row["distance"]
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
        return medicine, chunk, vector_score

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

    async def _bm25_search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int,
    ) -> list[tuple[MedicineInfo, list[ChunkMatch]]]:
        """Tsvector 풀텍스트 검색 — content_tsv @@ plainto_tsquery + ts_rank.

        28번 마이그의 ``content_tsv`` 컬럼 + GIN 인덱스 활용. RRF 의 BM25 source.
        한국어 query 는 simple config 의 단어 토큰화를 사용 (mecab-ko 미설치).
        """
        normalized = self._normalize_query_for_tsquery(query)
        if not normalized:
            return []

        sql, params = self._build_bm25_search_sql(normalized, filters, limit)
        rows = await connections.get("default").execute_query_dict(sql, params)
        logger.info("[RAG] tsvector(bm25): %d rows query=%r", len(rows), normalized[:50])
        # ts_rank 점수를 vector_score 자리에 그대로 넣음 (ChunkMatch 가 단일 score 필드만 보유)
        raw_hits = [self._row_to_hit(row) for row in rows]
        return self._group_chunks_by_medicine(raw_hits)

    @staticmethod
    def _normalize_query_for_tsquery(query: str) -> str:
        """한국어 query → plainto_tsquery 입력. stopword 제거 + 공백 결합."""
        words = re.findall(r"[가-힣a-zA-Z0-9]+", query)
        kept = [w for w in words if w.lower() not in _STOP_WORDS and len(w) > 1]
        return " ".join(kept)

    @staticmethod
    def _build_bm25_search_sql(
        normalized_query: str,
        filters: SearchFilters,
        limit: int,
    ) -> tuple[str, list]:
        """Tsvector @@ plainto_tsquery + ts_rank ORDER BY rank DESC LIMIT N."""
        where_conditions: list[str] = ["mc.content_tsv @@ plainto_tsquery('simple', $1)"]
        params: list = [normalized_query]
        idx = 2
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
            (1 - ts_rank(mc.content_tsv, plainto_tsquery('simple', $1))) AS distance,
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
        ORDER BY ts_rank(mc.content_tsv, plainto_tsquery('simple', $1)) DESC
        LIMIT ${idx}
        """  # noqa: S608  # nosec B608
        params.append(limit)
        return sql, params

    def _group_by_medicine(
        self,
        merged: list[dict],
        limit: int,
    ) -> list[SearchResult]:
        """RRF 결과 (chunk 단위) → medicine 단위 SearchResult 로 grouping.

        같은 medicine 의 chunk RRF score 를 합산해 final_score 로 사용.
        """
        by_medicine: dict[int, dict] = {}
        for item in merged:
            medicine: MedicineInfo = item["medicine"]
            mid = medicine.id
            if mid not in by_medicine:
                by_medicine[mid] = {
                    "medicine": medicine,
                    "chunks": [],
                    "score_sum": 0.0,
                }
            by_medicine[mid]["chunks"].append(item["match"])
            by_medicine[mid]["score_sum"] += item.get("rrf_score", 0.0)

        results: list[SearchResult] = []
        for entry in by_medicine.values():
            chunks = entry["chunks"]
            top_chunk_score = chunks[0].vector_score if chunks else 0.0
            results.append(
                SearchResult(
                    medicine=entry["medicine"],
                    matched_chunks=chunks,
                    vector_score=top_chunk_score,
                    keyword_score=0.0,  # legacy 필드 — RRF 도입 후 의미 X
                    final_score=entry["score_sum"],
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:limit]
