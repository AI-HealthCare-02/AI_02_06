"""Unit tests for HybridRetriever 의 halfvec(3072) 캐스팅.

PLAN.md (feat/halfvec-hnsw-rag) §1 — 마이그 29번에서 medicine_chunk.embedding
컬럼을 vector(3072) -> halfvec(3072) 로 변환했으므로, query 측 SQL 도
``$1::halfvec(3072)`` 로 명시적 캐스팅이 들어가야 HNSW 인덱스
(halfvec_cosine_ops) 가 정확히 적용된다.

본 테스트는 SQL 빌더가 두 곳 모두에 캐스팅을 포함하는지 검증한다:
- WHERE 절: ``(mc.embedding <=> $1::halfvec(3072)) < $2``
- SELECT 절: ``(mc.embedding <=> $1::halfvec(3072)) AS distance``
"""

from __future__ import annotations

from app.dtos.rag import SearchFilters
from app.services.rag.retrievers.hybrid import HybridRetriever


class TestVectorSearchSqlHalfvecCast:
    """_build_vector_search_sql 의 halfvec 캐스팅 검증."""

    def test_where_clause_casts_to_halfvec(self) -> None:
        """WHERE 절의 cosine distance 비교가 ``$1::halfvec(3072)`` 로 캐스팅."""
        embedding = [0.1] * 3072
        sql, _ = HybridRetriever._build_vector_search_sql(
            query_embedding=embedding,
            filters=SearchFilters(),
            similarity_threshold=0.5,
            limit=15,
        )
        assert "(mc.embedding <=> $1::halfvec(3072)) < $2" in sql

    def test_select_clause_casts_to_halfvec(self) -> None:
        """SELECT 절의 distance 계산도 동일한 ``$1::halfvec(3072)`` 캐스팅."""
        embedding = [0.1] * 3072
        sql, _ = HybridRetriever._build_vector_search_sql(
            query_embedding=embedding,
            filters=SearchFilters(),
            similarity_threshold=0.5,
            limit=15,
        )
        assert "(mc.embedding <=> $1::halfvec(3072)) AS distance" in sql

    def test_params_include_vector_string_and_threshold(self) -> None:
        """params 첫 두 슬롯은 vector 문자열 + (1 - threshold)."""
        embedding = [0.5, 0.25, 0.125]
        sql, params = HybridRetriever._build_vector_search_sql(
            query_embedding=embedding,
            filters=SearchFilters(),
            similarity_threshold=0.5,
            limit=15,
        )
        del sql
        assert params[0] == "[0.5,0.25,0.125]"
        assert params[1] == 0.5  # 1 - 0.5
        assert params[-1] == 15  # limit

    def test_medicine_name_filter_keeps_halfvec_cast(self) -> None:
        """필터 추가 시에도 halfvec 캐스팅 유지."""
        embedding = [0.1] * 3072
        sql, params = HybridRetriever._build_vector_search_sql(
            query_embedding=embedding,
            filters=SearchFilters(medicine_names=["타이레놀"]),
            similarity_threshold=0.5,
            limit=15,
        )
        assert "(mc.embedding <=> $1::halfvec(3072)) < $2" in sql
        assert "mi.medicine_name = ANY($3)" in sql
        assert params[2] == ["타이레놀"]
