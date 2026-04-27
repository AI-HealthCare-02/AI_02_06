"""RQ 기반 LLM 어댑터 (FastAPI 측).

옵션 C 이후 본 어댑터의 호출자는 ``session_compact_service`` 의
``summarize_messages`` 만 남았다. 다른 LLM 호출 (Router LLM, 2nd LLM,
RAG retrieval) 은 모두 ``app/services/tools/rq_adapters.py`` 의 전용 함수
들이 담당한다.

Design rationale:
- FastAPI 이미지는 ``openai`` 라이브러리를 직접 호출하지 않는다.
  ``rq.Queue.enqueue`` 와 DTO 재포장용 import 만 남긴다.
- 폴링 루프는 ``asyncio.sleep`` 으로 FastAPI 이벤트 루프를 막지 않는다.
"""

import asyncio
import time
from typing import Any

from rq import Queue

from app.dtos.rag import (
    ChatCompletion,
    SummaryResult,
    SummaryStatus,
    TokenUsage,
)

_DEFAULT_POLL_INTERVAL_SEC = 0.1
_DEFAULT_TIMEOUT_SEC = 60.0  # LLM은 임베딩보다 느리므로 더 긴 상한.
_GENERATE_JOB_REF = "ai_worker.domains.rag.jobs.generate_chat_response_job"
_COMPACT_JOB_REF = "ai_worker.domains.session_compact.jobs.compact_messages_job"


class LLMTimeoutError(TimeoutError):
    """LLM RQ job 이 timeout 내 완료되지 않았을 때."""


class LLMJobError(RuntimeError):
    """LLM RQ job 이 실패 상태로 종료됐을 때."""


class RQRAGGenerator:
    """RQ-backed LLM adapter — 옵션 C 이후로는 summarize 전용.

    FastAPI 측에서 OpenAI API 를 직접 호출하지 않고 ai-worker 의 RQ job 에
    위임한다. Router LLM / 2nd LLM / retrieval 은 ``app/services/tools/
    rq_adapters.py`` 가 담당하므로 본 클래스의 잔여 메서드는 세션 요약
    경로 (``summarize_messages``) 와 LLM 응답 생성 (``generate_chat_response``)
    뿐이다.
    """

    def __init__(
        self,
        queue: "Queue",
        *,
        poll_interval: float = _DEFAULT_POLL_INTERVAL_SEC,
        timeout: float = _DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._queue = queue
        self._poll_interval = poll_interval
        self._timeout = timeout

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> ChatCompletion:
        """Enqueue a chat generation job and return the DTO."""
        job = self._queue.enqueue(_GENERATE_JOB_REF, messages, system_prompt)
        raw = await self._await_result(job)
        return _to_chat_completion(raw)

    async def summarize_messages(
        self,
        messages: list[dict[str, str]],
        prev_summary: str | None = None,
    ) -> SummaryResult:
        """Enqueue a session-compact job and return the DTO."""
        job = self._queue.enqueue(_COMPACT_JOB_REF, messages, prev_summary)
        raw = await self._await_result(job)
        return _to_summary_result(raw)

    # ── Internals ────────────────────────────────────────────────

    async def _await_result(self, job: Any) -> dict[str, Any]:
        deadline = time.monotonic() + self._timeout

        while True:
            job.refresh()
            status = job.get_status()

            if status == "finished":
                return job.result

            if status == "failed":
                raise LLMJobError(job.exc_info or "AI-Worker LLM job failed")

            if time.monotonic() >= deadline:
                raise LLMTimeoutError(f"LLM job did not finish within {self._timeout}s")

            await asyncio.sleep(self._poll_interval)


# ── dict → DTO 변환 ────────────────────────────────────────────


def _to_chat_completion(raw: dict[str, Any]) -> ChatCompletion:
    usage_raw = raw.get("token_usage")
    token_usage = TokenUsage(**usage_raw) if usage_raw else None
    return ChatCompletion(answer=raw["answer"], token_usage=token_usage)


def _to_summary_result(raw: dict[str, Any]) -> SummaryResult:
    usage_raw = raw.get("token_usage")
    token_usage = TokenUsage(**usage_raw) if usage_raw else None
    return SummaryResult(
        status=SummaryStatus(raw["status"]),
        summary=raw.get("summary", ""),
        consumed_message_count=raw.get("consumed_message_count", 0),
        token_usage=token_usage,
    )
