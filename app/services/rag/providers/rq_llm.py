"""RQ 기반 RAGGenerator 어댑터 (FastAPI 측).

``RAGPipeline`` 은 ``RAGGenerator`` 인스턴스를 ``rag_generator=`` 로 주입받아
``rewrite_query`` / ``generate_chat_response`` 를 호출한다. 본 어댑터는 이
공개 메서드 두 개를 그대로 구현하되, OpenAI 호출을 직접 수행하지 않고
Redis Queue("ai") 에 ``rewrite_query_job`` / ``generate_chat_response_job``
을 enqueue한 뒤 결과를 기다려 ``RewriteResult`` / ``ChatCompletion`` DTO
로 재포장한다.

Design rationale:
- FastAPI 이미지는 ``openai`` 라이브러리를 더 이상 직접 호출하지 않아도
  되지만, ``rq.Queue.enqueue`` 와 DTO 재포장용 import 만 남긴다.
- 시그니처 동치성 덕분에 ``RAGPipeline`` 코드는 수정 불필요.
- 폴링 루프는 ``asyncio.sleep`` 으로 FastAPI 이벤트 루프를 막지 않는다.
"""

import asyncio
import time
from typing import Any

try:
    from rq import Queue  # pragma: no cover — type hint only
except ImportError:  # pragma: no cover
    Queue = Any  # type: ignore[misc, assignment]

from app.dtos.rag import (
    ChatCompletion,
    RewriteResult,
    RewriteStatus,
    SummaryResult,
    SummaryStatus,
    TokenUsage,
)

_DEFAULT_POLL_INTERVAL_SEC = 0.1
_DEFAULT_TIMEOUT_SEC = 60.0  # LLM은 임베딩보다 느리므로 더 긴 상한.
_REWRITE_JOB_REF = "ai_worker.tasks.rag_tasks.rewrite_query_job"
_GENERATE_JOB_REF = "ai_worker.tasks.rag_tasks.generate_chat_response_job"
_COMPACT_JOB_REF = "ai_worker.tasks.compact_tasks.compact_messages_job"


class LLMTimeoutError(TimeoutError):
    """LLM RQ job 이 timeout 내 완료되지 않았을 때."""


class LLMJobError(RuntimeError):
    """LLM RQ job 이 실패 상태로 종료됐을 때."""


class RQRAGGenerator:
    """RAGGenerator-shaped adapter that delegates to AI-Worker via RQ.

    ``RAGPipeline`` uses this in place of the legacy ``RAGGenerator`` so
    that OpenAI API calls happen inside the AI-Worker process while
    FastAPI only deals with HTTP I/O and Redis roundtrips.
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

    async def rewrite_query(
        self,
        history: list[dict[str, str]],
        current_query: str,
    ) -> RewriteResult:
        """Enqueue a rewrite job and return the DTO the pipeline expects."""
        job = self._queue.enqueue(_REWRITE_JOB_REF, history, current_query)
        raw = await self._await_result(job)
        return _to_rewrite_result(raw)

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


def _to_rewrite_result(raw: dict[str, Any]) -> RewriteResult:
    usage_raw = raw.get("token_usage")
    token_usage = TokenUsage(**usage_raw) if usage_raw else None
    return RewriteResult(
        status=RewriteStatus(raw["status"]),
        query=raw["query"],
        token_usage=token_usage,
    )


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
