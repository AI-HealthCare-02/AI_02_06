"""Session-compact RQ jobs — Phase Z.

FastAPI 측 ``SessionCompactService`` 가 ``ai`` 큐로 enqueue 한다. 오염
필터(out_of_scope / general_chat 제거) 는 FastAPI 측에서 미리 수행된다고
가정하며, 본 워커 측 job 은 LLM 호출과 직렬화만 담당한다.

job 함수 안의 lazy import 는 ``ai_worker/domains/rag/jobs.py`` 와 동일한
의도 — worker cold start 단축 (CLAUDE.md §8.5 의 lazy 금지 정책 예외).
"""


async def compact_messages_job(
    messages: list[dict[str, str]],
    prev_summary: str | None = None,
) -> dict:
    """[RQ Task] 세션 메시지 묶음을 의료 컨텍스트 요약으로 압축.

    Args:
        messages: 시간순 메시지 리스트 (오염 필터 통과 후).
        prev_summary: 이전 요약. 첫 호출이면 ``None``.

    Returns:
        ``{"status", "summary", "consumed_message_count", "token_usage"}``.
        ``status`` 는 ``"ok" | "empty" | "fallback"``.
    """
    from ai_worker.domains.session_compact.summarizer import summarize_session_messages

    result = await summarize_session_messages(messages=messages, prev_summary=prev_summary)
    return {
        "status": result.status.value,
        "summary": result.summary,
        "consumed_message_count": result.consumed_message_count,
        "token_usage": result.token_usage.model_dump() if result.token_usage is not None else None,
    }
