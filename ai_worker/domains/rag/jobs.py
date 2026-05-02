"""RAG RQ jobs — FastAPI 가 ``ai`` 큐로 enqueue 하는 진입점.

RAG 4단 파이프라인 (PLAN feature/RAG) 에서 1개의 RQ task 만 노출:

- ``generate_chat_response_job`` → ``response_generator.generate_response``

이전 ``embed_text_job`` (ko-sroberta) 는 폐기. query 측 임베딩은 FastAPI 의
``app.services.rag.openai_embedding`` 이 직접 OpenAI API 호출.
"""

import logging

logger = logging.getLogger(__name__)


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

    # ── 진단 로그 (diag/2nd-llm-input-output-logging) ─────────────────
    # 흐름: 2nd LLM 호출 직전 system_prompt + messages 전체 dump
    sp = system_prompt or ""
    logger.info(
        "[LLM-Diag] INPUT system_prompt[%dchars]=%r messages_count=%d last_user=%r",
        len(sp),
        sp,
        len(messages),
        (messages[-1].get("content") if messages else "")[:300],
    )

    result = await generate_response(messages=messages, system_prompt=system_prompt)

    answer = result.answer or ""
    logger.info(
        "[LLM-Diag] OUTPUT answer[%dchars]=%r token_usage=%s",
        len(answer),
        answer,
        result.token_usage.model_dump() if result.token_usage is not None else None,
    )

    return {
        "answer": answer,
        "token_usage": result.token_usage.model_dump() if result.token_usage is not None else None,
    }
