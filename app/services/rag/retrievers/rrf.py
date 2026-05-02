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
        rank_lists: 각 list 는 동일 도메인 ID 의 ranked sequence (rank 1 이 첫 원소).
        k: RRF 분모 상수. 기본 60.

    Returns:
        (id, score) tuple list. score 내림차순. 중복 id 는 합산.
    """
    scores: dict[int, float] = {}
    for rank_list in rank_lists:
        for rank_idx, item_id in enumerate(rank_list, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank_idx)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _rank_chunks(hits: list[dict[str, Any]]) -> dict[int, int]:
    """Chunk dict list → {chunk_id: 1-based rank}."""
    return {chunk["chunk_id"]: i for i, chunk in enumerate(hits, start=1) if "chunk_id" in chunk}


def rrf_intra_query(
    vector_hits: list[dict[str, Any]],
    bm25_hits: list[dict[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """1차 RRF — 단일 query 의 vector + BM25 결과 병합.

    Args:
        vector_hits: pgvector cosine 결과 (chunk_id 포함 dict list).
        bm25_hits: tsvector 풀텍스트 결과 (chunk_id 포함 dict list).
        k: RRF k. 기본 60.

    Returns:
        병합된 chunk dict list — RRF score 내림차순. 각 chunk 에 'rrf_score' 키 추가.
    """
    vector_ranks = _rank_chunks(vector_hits)
    bm25_ranks = _rank_chunks(bm25_hits)

    # chunk_id 별 dict 병합 (vector hit 우선, bm25 only 인 chunk 도 포함)
    by_id: dict[int, dict[str, Any]] = {}
    for chunk in vector_hits:
        cid = chunk.get("chunk_id")
        if cid is not None:
            by_id[cid] = dict(chunk)
    for chunk in bm25_hits:
        cid = chunk.get("chunk_id")
        if cid is not None and cid not in by_id:
            by_id[cid] = dict(chunk)

    # RRF score 계산
    scored: list[tuple[float, dict[str, Any]]] = []
    for cid, chunk in by_id.items():
        score = 0.0
        if cid in vector_ranks:
            score += 1.0 / (k + vector_ranks[cid])
        if cid in bm25_ranks:
            score += 1.0 / (k + bm25_ranks[cid])
        chunk["rrf_score"] = score
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored]


def rrf_cross_query(
    per_query_results: list[list[dict[str, Any]]],
    final_cap: int = 15,
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """2차 RRF — N 개 query 결과 list 들을 cross-merge + final_cap.

    Args:
        per_query_results: 각 element 는 한 query 의 1차 RRF 결과.
            각 chunk dict 에 chunk_id 키 필수.
        final_cap: 최종 반환 chunk 수 상한. 기본 15.
        k: RRF k. 기본 60.

    Returns:
        unique chunk dict list — RRF score 내림차순. len ≤ final_cap.
        각 chunk 에 'cross_rrf_score' 키 추가.
    """
    by_id: dict[int, dict[str, Any]] = {}
    scores: dict[int, float] = {}

    for query_result in per_query_results:
        for rank_idx, chunk in enumerate(query_result, start=1):
            cid = chunk.get("chunk_id")
            if cid is None:
                continue
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank_idx)
            if cid not in by_id:
                by_id[cid] = dict(chunk)

    # 정렬 + cap
    sorted_ids = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:final_cap]
    out: list[dict[str, Any]] = []
    for cid, score in sorted_ids:
        chunk = by_id[cid]
        chunk["cross_rrf_score"] = score
        out.append(chunk)
    return out
