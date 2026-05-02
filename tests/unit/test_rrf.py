"""Unit tests for app.services.rag.retrievers.rrf — 2단 RRF (intra + cross).

PLAN.md §4.1 — Cormack 2009 표준 (k=60). Phase 3 [Implement] Green.
"""

from __future__ import annotations

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
    """rrf_merge 기본 단위."""

    def test_two_lists_merge(self) -> None:
        """두 rank list → 합산 score 반환."""
        list_a = [101, 102, 103]
        list_b = [102, 104, 101]
        result = rrf_merge([list_a, list_b])
        # 결과는 (id, score) tuple list, score 내림차순
        ids_in_order = [item_id for item_id, _ in result]
        # 101 과 102 가 양쪽 모두 등장 → 상위
        assert 101 in ids_in_order[:2]
        assert 102 in ids_in_order[:2]
        # 103, 104 는 한쪽만 → 하위
        assert 103 in ids_in_order[2:]
        assert 104 in ids_in_order[2:]

    def test_dedup(self) -> None:
        """동일 ID 가 양쪽 모두 있어도 결과는 unique."""
        result = rrf_merge([[1, 2, 3], [1, 2, 3]])
        ids = [item_id for item_id, _ in result]
        assert len(ids) == len(set(ids))  # unique


class TestRrfIntraQuery:
    """1차 RRF — vector + bm25 단일 query 병합."""

    def test_vector_only(self) -> None:
        """bm25 빈 list → vector 결과 그대로 (rrf_score 만 추가)."""
        vector_hits = [{"chunk_id": 1, "score": 0.9}, {"chunk_id": 2, "score": 0.8}]
        result = rrf_intra_query(vector_hits, [])
        assert len(result) == 2
        assert result[0]["chunk_id"] == 1  # rank 1 → 더 높은 RRF score
        assert result[0]["rrf_score"] > result[1]["rrf_score"]

    def test_combined(self) -> None:
        """vector + bm25 모두 → 둘 다에 등장한 chunk 가 상위."""
        vector_hits = [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}]
        bm25_hits = [{"chunk_id": 2}, {"chunk_id": 4}, {"chunk_id": 1}]
        result = rrf_intra_query(vector_hits, bm25_hits)
        ids = [c["chunk_id"] for c in result]
        # 1, 2 양쪽 모두 → 상위 2
        assert {ids[0], ids[1]} == {1, 2}
        # unique chunks
        assert len(set(ids)) == len(ids)


class TestRrfCrossQuery:
    """2차 RRF — N query 결과 cross-merge + final_cap."""

    def test_three_queries_merge_with_cap(self) -> None:
        """3 query → cross-merge → final_cap=5 적용."""
        per_query = [
            [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}],
            [{"chunk_id": 2}, {"chunk_id": 4}, {"chunk_id": 5}],
            [{"chunk_id": 3}, {"chunk_id": 6}, {"chunk_id": 1}],
        ]
        result = rrf_cross_query(per_query, final_cap=5)
        assert len(result) == 5
        # 각 chunk 에 cross_rrf_score 키 존재
        for chunk in result:
            assert "cross_rrf_score" in chunk

    def test_repeated_chunk_ranks_higher(self) -> None:
        """같은 chunk_id 가 여러 query 에서 1위 → RRF score 합산되어 최상위."""
        per_query = [
            [{"chunk_id": 99}, {"chunk_id": 1}],
            [{"chunk_id": 99}, {"chunk_id": 2}],
            [{"chunk_id": 99}, {"chunk_id": 3}],
        ]
        result = rrf_cross_query(per_query, final_cap=10)
        assert result[0]["chunk_id"] == 99  # 3번 1위 → 압도적

    def test_final_cap_respected(self) -> None:
        """final_cap=15 면 결과 길이 ≤ 15."""
        per_query = [[{"chunk_id": i} for i in range(20)] for _ in range(5)]
        result = rrf_cross_query(per_query, final_cap=15)
        assert len(result) == 15
