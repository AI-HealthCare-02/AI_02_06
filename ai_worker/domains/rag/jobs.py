"""RAG RQ jobs — FastAPI 가 ``ai`` 큐로 enqueue 하는 진입점.

옵션 C 이후의 두 RQ task (``rewrite_query_job`` 폐기됨):

- ``embed_text_job`` → ``embedding_provider.encode_text``
- ``generate_chat_response_job`` → ``response_generator.generate_response``

각 job 함수 안에서 implementation 모듈을 lazy import 하는 이유:
worker process 의 cold start latency (sentence-transformers / torch /
transformers 같은 무거운 의존성 로드) 를 첫 task 시점까지 미루기 위함.
CLAUDE.md §8.5 의 lazy import 금지 정책 예외 (성능 critical path).
"""


async def embed_text_job(text: str) -> list[float]:
    """[RQ Task] 쿼리 임베딩 (768차원 L2-정규화 벡터).

    Args:
        text: 임베딩 대상 문자열.

    Returns:
        768차원 float 리스트.
    """
    from ai_worker.domains.rag.embedding_provider import encode_text

    return await encode_text(text)


async def generate_chat_response_job(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
) -> dict:
    """[RQ Task] 최종 답변 생성.

    Args:
        messages: 대화 턴 리스트 (마지막은 사용자 질문).
        system_prompt: 검색 컨텍스트가 삽입된 system prompt (옵션).

    Returns:
        ``{"answer", "token_usage"}`` 형태 dict.
    """
    from ai_worker.domains.rag.response_generator import generate_response

    result = await generate_response(messages=messages, system_prompt=system_prompt)
    return {
        "answer": result.answer,
        "token_usage": result.token_usage.model_dump() if result.token_usage is not None else None,
    }
