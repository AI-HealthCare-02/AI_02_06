"""OpenAI text-embedding-3-large query-side 임베딩 — 3072d.

PLAN.md (feature/RAG) §0 결정 — chunk 임베딩과 동일 모델/dim 사용.

medicine_chunk 의 embedding 컬럼은 vector(3072) (28번 마이그). 사용자 query 도
같은 모델 + 같은 dim 으로 임베딩해야 cosine 유사도 비교 정확.

사용처:
- RRF Hybrid Retrieval 의 vector 검색 step
- 다음 사이클 (29번 마이그) 의 ANN 인덱스 검색

ai_worker 측의 embed_text_job 과 분리:
- ai_worker: medicine_chunk batch 임베딩 (scripts/embed_medicine_chunks.py 가 처리)
- app/services: 사용자 query 단건 임베딩 (RAG retrieval 시 호출)

batch 입력 지원 (fanout_queries N 개를 한 번에 임베딩).
"""

from openai import AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072


async def encode_query(query: str) -> list[float]:
    """단일 query 를 3072d 임베딩 벡터로 변환.

    Args:
        query: 사용자 query 또는 fanout_query 문자열.

    Returns:
        3072 float 의 list. cosine 유사도 비교용 L2 정규화는 OpenAI 측 자동.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del query
    msg = "encode_query 는 Phase 3 [Implement] 에서 AsyncOpenAI.embeddings.create 호출로 채움"
    raise NotImplementedError(msg)


async def encode_queries_batch(queries: list[str]) -> list[list[float]]:
    """여러 query 를 batch 로 한 번에 임베딩.

    fanout_queries N 개를 단일 OpenAI API 호출로 처리해 latency 최소화.

    Args:
        queries: query 문자열 list. 빈 list 면 빈 list 반환.

    Returns:
        각 query 에 대응하는 3072d 임베딩 list 의 list.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del queries
    msg = "encode_queries_batch 는 Phase 3 [Implement] 에서 batch input 으로 채움"
    raise NotImplementedError(msg)


def _get_client() -> AsyncOpenAI | None:
    """AsyncOpenAI 싱글톤 — Phase 3 에서 ai_worker.core.openai_client 패턴 재사용."""
    msg = "client factory 는 Phase 3 [Implement] 에서 채움"
    raise NotImplementedError(msg)
