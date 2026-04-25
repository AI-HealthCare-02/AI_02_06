"""Session-compact RQ tasks (AI-Worker only).

Async RQ job for Phase Z session summarisation. FastAPI enqueues this
job via the ``ai`` queue whenever a chat session accumulates enough new
messages to warrant compaction. Pollution filtering (out_of_scope /
general_chat removal) happens on the FastAPI side in
``SessionCompactService`` before enqueue — this worker-side function
trusts the payload and only calls the LLM.
"""


async def compact_messages_job(
    messages: list[dict[str, str]],
    prev_summary: str | None = None,
) -> dict:
    """세션 메시지 묶음을 의료 컨텍스트 중심 요약으로 압축한다.

    Args:
        messages: 시간순(오래된 것 먼저) 메시지 리스트. 각 항목은
            ``{"role": "user"|"assistant", "content": str}`` 형식이며
            FastAPI 측에서 오염 필터(OUT_OF_SCOPE / GENERAL_CHAT 제거)를
            이미 통과한 상태여야 한다.
        prev_summary: 기존 세션 요약. 첫 compact 이거나 이전 요약이 없으면
            ``None``.

    Returns:
        ``{"status", "summary", "consumed_message_count", "token_usage"}``
        형태의 dict. ``status`` 는 ``"ok" | "empty" | "fallback"``.
    """
    from ai_worker.providers.llm import summarize_messages

    return await summarize_messages(messages=messages, prev_summary=prev_summary)
