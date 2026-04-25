"""RAG RQ tasks (AI-Worker only).

Async RQ job functions that FastAPI enqueues via the "ai" queue so that
ML workloads stay inside the AI-Worker process:

- embed_text_job            — 쿼리 임베딩 (ko-sroberta, ThreadPool offload)
- rewrite_query_job         — 대화 맥락 기반 쿼리 재작성 (AsyncOpenAI 싱글톤)
- generate_chat_response_job — 최종 답변 생성 (AsyncOpenAI 싱글톤)

FastAPI side enqueues via ``rq.Queue("ai").enqueue(...)`` and awaits
the result with an async-friendly wrapper (``RQEmbeddingProvider``
for embed, 후속 어댑터가 LLM 쪽도 동일 패턴으로 중개한다).
"""


async def embed_text_job(text: str) -> list[float]:
    """쿼리 텍스트를 768차원 L2-정규화 벡터로 임베딩한다.

    Phase X-2에서 AI-Worker 싱글톤 모델 + ThreadPool 경로로 연결됨.
    FastAPI가 RQ "ai" 큐에 이 함수를 enqueue하면 AI-Worker가 처리한다.

    Args:
        text: 임베딩 대상 문자열.

    Returns:
        768차원 L2-정규화 float 리스트.
    """
    from ai_worker.providers.embedding import encode_text

    return await encode_text(text)


async def rewrite_query_job(
    history: list[dict[str, str]],
    current_query: str,
) -> dict:
    """대화 맥락을 반영해 사용자 쿼리를 self-contained 한 문장으로 재작성.

    Args:
        history: 직전 대화 턴 리스트 (각 항목 ``{"role", "content"}``).
        current_query: 사용자의 이번 턴 쿼리.

    Returns:
        ``{"status", "query", "token_usage"}`` 형태의 dict.
    """
    from ai_worker.providers.llm import rewrite_query

    return await rewrite_query(history=history, current_query=current_query)


async def generate_chat_response_job(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
) -> dict:
    """준비된 메시지 리스트 + system prompt 로 최종 답변 생성.

    컨텍스트(검색된 청크)는 FastAPI 측 ``RAGPipeline._build_context`` 가
    ``system_prompt`` 안에 삽입해 전달한다. 이 job 은 LLM API 호출과
    결과 직렬화만 담당한다.

    Args:
        messages: ``user``/``assistant`` 턴 리스트 (최신 사용자 질문 포함).
        system_prompt: 완성된 system prompt (컨텍스트 포함). ``None`` 이면
            persona-only 폴백 프롬프트가 적용된다.

    Returns:
        ``{"answer", "token_usage"}`` 형태의 dict.
    """
    from ai_worker.providers.llm import generate_chat_response

    return await generate_chat_response(messages, system_prompt=system_prompt)
