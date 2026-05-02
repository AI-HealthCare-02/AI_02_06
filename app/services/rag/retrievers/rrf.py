"""Reciprocal Rank Fusion (RRF) 2단 알고리즘 — intra-query + cross-query.

PLAN.md (feature/RAG) §3 C2 — Cormack et al. 2009 표준 (k=60).

2단 RRF:
  1차 (intra-query): 단일 query 안에서 vector rank ↔ BM25 (tsvector) rank 병합
       각 query 당 K=5 chunk 회수 (final_cap 적용 전)
  2차 (cross-query): N 개 query 의 결과 list 들을 cross-merge
       final_cap=15 unique chunks (중복 chunk 는 RRF score 가산되어 상위 ranking)

수식:
    score(d) = Σ 1 / (k + rank_i(d))     (k=60 표준)

여기서 d = 단일 chunk_id, rank_i = i 번째 source 에서의 d 의 1-based rank.
한 source 에 d 가 없으면 그 항은 0 (RRF 의 자연 dedup 효과).
"""

from typing import Any

RRF_K = 60  # Cormack et al. 2009 표준


def rrf_merge(rank_lists: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """N 개의 rank list 를 RRF score 기준으로 병합.

    Args:
        rank_lists: 각 list 는 동일 도메인 ID (예: chunk_id) 의 ranked sequence.
            첫 element 가 rank 1, 두 번째가 rank 2, ...
        k: RRF 분모 상수. 기본 60.

    Returns:
        (id, score) tuple list. score 내림차순 정렬. 중복 id 는 합산.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del rank_lists, k
    msg = "rrf_merge 는 Phase 3 [Implement] 에서 채움"
    raise NotImplementedError(msg)


def rrf_intra_query(
    vector_hits: list[dict[str, Any]],
    bm25_hits: list[dict[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """1차 RRF — 단일 query 의 vector + BM25 결과 병합.

    Args:
        vector_hits: pgvector cosine 검색 결과 (chunk_id 포함 dict list).
        bm25_hits: tsvector 풀텍스트 검색 결과 (chunk_id 포함 dict list).
        k: RRF k. 기본 60.

    Returns:
        병합된 chunk dict list — RRF score 내림차순.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del vector_hits, bm25_hits, k
    msg = "rrf_intra_query 는 Phase 3 [Implement] 에서 채움"
    raise NotImplementedError(msg)


def rrf_cross_query(
    per_query_results: list[list[dict[str, Any]]],
    final_cap: int = 15,
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """2차 RRF — N 개 query 결과 list 들을 cross-merge + final_cap.

    Args:
        per_query_results: 각 element 는 한 query 의 1차 RRF 결과 (intra-query
            병합된 chunk list). 각 chunk dict 에 chunk_id 키 필수.
        final_cap: 최종 반환 chunk 수 상한. 기본 15.
        k: RRF k. 기본 60.

    Returns:
        unique chunk dict list — RRF score 내림차순. len ≤ final_cap.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del per_query_results, final_cap, k
    msg = "rrf_cross_query 는 Phase 3 [Implement] 에서 채움"
    raise NotImplementedError(msg)
