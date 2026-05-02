"""Unit tests for app.services.rag.retrievers.rrf — 2단 RRF (intra + cross).

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 RRF 표준 공식 검증으로 전환.

PLAN.md §4.1 — Cormack 2009 표준 (k=60):
- 1차 RRF: vector top-5 + bm25 top-5 → 단일 query 병합
- 2차 RRF: 3 query 의 결과 list → cross-merge → final_cap=15
- 같은 chunk 가 여러 query 에서 등장 → RRF score 가산되어 상위 ranking
- k=60 표준 점수 공식 검증
- dedup (unique chunk_id 만 반환)
"""

from __future__ import annotations

import pytest

from app.services.rag.retrievers.rrf import (
    RRF_K,
    rrf_cross_query,
    rrf_intra_query,
    rrf_merge,
)


class TestConstants:
    """RRF k 상수 표준 (Cormack 2009)."""

    def test_k_is_60(self) -> None:
        assert RRF_K == 60


class TestRrfMerge:
    """rrf_merge 기본 단위 (Red 상태)."""

    def test_two_lists_merge(self) -> None:
        """두 rank list → 합산 score 반환."""
        list_a = [101, 102, 103]
        list_b = [102, 104, 101]
        with pytest.raises(NotImplementedError):
            rrf_merge([list_a, list_b])

    def test_dedup(self) -> None:
        """동일 ID 가 양쪽 모두 있어도 결과는 unique."""
        with pytest.raises(NotImplementedError):
            rrf_merge([[1, 2, 3], [1, 2, 3]])


class TestRrfIntraQuery:
    """1차 RRF — vector + bm25 단일 query 병합 (Red)."""

    def test_vector_only(self) -> None:
        """bm25 빈 list → vector 결과 그대로."""
        vector_hits = [{"chunk_id": 1, "score": 0.9}, {"chunk_id": 2, "score": 0.8}]
        with pytest.raises(NotImplementedError):
            rrf_intra_query(vector_hits, [])

    def test_combined(self) -> None:
        """vector + bm25 모두 → 둘 다에 등장한 chunk 가 상위."""
        vector_hits = [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}]
        bm25_hits = [{"chunk_id": 2}, {"chunk_id": 4}, {"chunk_id": 1}]
        with pytest.raises(NotImplementedError):
            rrf_intra_query(vector_hits, bm25_hits)


class TestRrfCrossQuery:
    """2차 RRF — N query 결과 cross-merge + final_cap (Red)."""

    def test_three_queries_merge_with_cap(self) -> None:
        """3 query → cross-merge → final_cap=5 적용."""
        per_query = [
            [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}],
            [{"chunk_id": 2}, {"chunk_id": 4}, {"chunk_id": 5}],
            [{"chunk_id": 3}, {"chunk_id": 6}, {"chunk_id": 1}],
        ]
        with pytest.raises(NotImplementedError):
            rrf_cross_query(per_query, final_cap=5)

    def test_repeated_chunk_ranks_higher(self) -> None:
        """같은 chunk_id 가 여러 query 에서 1위 → RRF score 합산되어 최상위."""
        per_query = [
            [{"chunk_id": 99}, {"chunk_id": 1}],
            [{"chunk_id": 99}, {"chunk_id": 2}],
            [{"chunk_id": 99}, {"chunk_id": 3}],
        ]
        with pytest.raises(NotImplementedError):
            rrf_cross_query(per_query, final_cap=10)

    def test_final_cap_respected(self) -> None:
        """final_cap=15 면 결과 길이 ≤ 15."""
        per_query = [[{"chunk_id": i} for i in range(20)] for _ in range(5)]
        with pytest.raises(NotImplementedError):
            rrf_cross_query(per_query, final_cap=15)
