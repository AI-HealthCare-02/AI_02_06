"""RAG retrieval — medicine_chunk hybrid 검색 (vector + tsvector RRF).

ai-worker 의 fan-out tool 호출 (``search_medicine_knowledge_base`` x N) 분기에서
호출된다. 호출자는 Tortoise lifecycle 을 직접 관리한다.

흐름: query 임베딩 (OpenAI 3-large) -> HybridRetriever.retrieve (RRF) -> chunk 직렬화
"""

import logging
from typing import Any

from app.dtos.rag import SearchFilters, SearchResult
from app.services.rag.openai_embedding import EMBEDDING_DIMENSIONS, encode_query
from app.services.rag.retrievers.hybrid import HybridRetriever

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 5


class _UnusedEmbeddingProvider:
    """HybridRetriever 의 ``embedding_provider`` 인자 형식 만족용 stub.

    ``HybridRetriever.retrieve()`` 는 provider 를 호출하지 않고
    ``query_embedding`` 인자로 받은 사전계산 벡터만 사용한다.
    """

    @property
    def dimensions(self) -> int:
        return EMBEDDING_DIMENSIONS

    async def encode_single(self, text: str) -> list[float]:
        del text
        raise NotImplementedError("worker-side retrieval uses encode_query directly")

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        del texts
        raise NotImplementedError("worker-side retrieval uses encode_query directly")


# ── RAG retrieval (Router LLM tool dispatch) ────────────────────────
# 흐름: 빈 쿼리 차단 -> 임베딩 (사전계산 우선) -> HybridRetriever 검색 -> chunk 직렬화
async def retrieve_medicine_chunks(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    *,
    precomputed_embedding: list[float] | None = None,
) -> dict[str, Any]:
    """Query 를 임베딩하고 hybrid 검색해 chunk 직렬화 결과를 반환한다.

    Tortoise 가 이미 init 된 상태에서 호출되어야 한다 (호출자의 lifecycle 관리).

    Args:
        query: 검색 질의 (fan-out 으로 만들어진 1개 쿼리).
        max_results: 반환 SearchResult 상한 (실제 chunk 수는 result 당 N 청크).
        precomputed_embedding: 호출자가 batch 임베딩으로 사전 계산한 3072d 벡터.
            전달 시 OpenAI 임베딩 API 호출을 skip — fan-out N 개 쿼리를
            1회 batch 로 묶어 응답 속도/비용 최적화에 사용.

    Returns:
        ``{"chunks": [{"medicine_name", "section", "content", "score"}, ...]}``
        — 빈 결과면 ``chunks=[]``. 모두 RQ pickle 안전한 dict.
    """
    cleaned = query.strip() if query else ""
    if not cleaned:
        logger.warning("[RAG dispatch] empty query, returning empty chunks")
        return {"chunks": [], "note": "empty query"}

    embedding = precomputed_embedding if precomputed_embedding is not None else await encode_query(cleaned)
    retriever = HybridRetriever(embedding_provider=_UnusedEmbeddingProvider())
    results = await retriever.retrieve(
        query=cleaned,
        query_embedding=embedding,
        filters=SearchFilters(),
        limit=max_results,
    )
    serialized = _serialize_chunks(results)
    logger.info(
        "[RAG dispatch] query=%r results=%d chunks=%d",
        cleaned[:50],
        len(results),
        len(serialized),
    )
    return {"chunks": serialized}


def _serialize_chunks(results: list[SearchResult]) -> list[dict[str, Any]]:
    """SearchResult 리스트 → 2nd LLM 친화 chunk dict 리스트.

    각 medicine 에 매칭된 모든 chunk 를 펼쳐 반환한다. score 는 chunk 별
    vector_score (cosine 유사도) 를 사용 — 2nd LLM 이 chunk 신뢰도 비교에 활용.
    """
    serialized: list[dict[str, Any]] = []
    for result in results:
        serialized.extend(
            {
                "medicine_name": result.medicine.medicine_name,
                "section": chunk_match.chunk.section,
                "content": chunk_match.chunk.content,
                "score": round(chunk_match.vector_score, 3),
            }
            for chunk_match in result.matched_chunks
        )
    return serialized
