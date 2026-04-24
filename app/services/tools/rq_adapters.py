"""RQ-backed adapters for the tool-calling subsystem (FastAPI side).

Mirrors the ``RQEmbeddingProvider`` pattern from RAG: FastAPI never holds
the OpenAI client nor the actual tool execution — it only enqueues an
AI-Worker RQ job and polls the result with ``asyncio.sleep`` so the event
loop stays free.

Two entry points:

- ``route_intent_via_rq(messages, queue)`` → ``RouteResult``
    Enqueues ``route_intent_job``. The worker returns the raw OpenAI
    assistant message dict; this adapter hands it to
    ``parse_router_response`` so the caller gets a domain DTO.

- ``run_tool_calls_via_rq(calls, queue)`` → ``{tool_call_id: result}``
    Enqueues ``run_tool_calls_job``. The worker already aggregates the
    parallel results into a pickle-safe dict, so no post-processing is
    needed. Empty ``calls`` short-circuits to ``{}`` without enqueueing.

Failures map to two dedicated exceptions — ``ToolTimeoutError`` (poll
deadline exceeded) and ``ToolJobError`` (RQ status transitioned to
"failed") — so the service layer can distinguish wait vs. worker errors.
"""

import asyncio
import time
from typing import Any

from app.services.tools.router import parse_router_response

try:
    from app.dtos.tools import RouteResult  # only the DTO is needed here
except ImportError:  # pragma: no cover — defensive; DTO always present in app runtime
    RouteResult = Any  # type: ignore[misc, assignment]

ROUTE_INTENT_JOB_REF = "ai_worker.tasks.tool_tasks.route_intent_job"
RUN_TOOL_CALLS_JOB_REF = "ai_worker.tasks.tool_tasks.run_tool_calls_job"

_DEFAULT_POLL_INTERVAL_SEC = 0.1
_DEFAULT_ROUTE_TIMEOUT_SEC = 30.0
_DEFAULT_RUN_TIMEOUT_SEC = 30.0


class ToolTimeoutError(TimeoutError):
    """Raised when a tool-calling RQ job does not finish before the deadline."""


class ToolJobError(RuntimeError):
    """Raised when a tool-calling RQ job transitions to a failed status."""


async def _await_result(
    job: Any,
    *,
    poll_interval: float,
    timeout: float,  # noqa: ASYNC109 — intentional deadline param; custom ToolTimeoutError precludes asyncio.timeout
) -> Any:
    """Poll an RQ ``Job`` until it finishes, fails, or the deadline passes.

    Args:
        job: Object exposing ``refresh()``, ``get_status()``, ``result``,
            ``exc_info`` — matches both the real ``rq.job.Job`` and the
            test ``_FakeJob`` stub.
        poll_interval: Seconds between status polls.
        timeout: Absolute wait cap in seconds.

    Returns:
        Whatever the worker produced for ``job.result``.

    Raises:
        ToolTimeoutError: If the deadline is reached before completion.
        ToolJobError: If the job reports a failed status.
    """
    deadline = time.monotonic() + timeout

    while True:
        job.refresh()
        status = job.get_status()

        if status == "finished":
            return job.result

        if status == "failed":
            raise ToolJobError(job.exc_info or "AI-Worker tool job failed")

        if time.monotonic() >= deadline:
            raise ToolTimeoutError(f"Tool job did not finish within {timeout}s")

        await asyncio.sleep(poll_interval)


async def route_intent_via_rq(
    *,
    messages: list[dict[str, Any]],
    queue: Any,
    poll_interval: float = _DEFAULT_POLL_INTERVAL_SEC,
    timeout: float = _DEFAULT_ROUTE_TIMEOUT_SEC,  # noqa: ASYNC109 — poll deadline; see _await_result
) -> "RouteResult":
    """Enqueue ``route_intent_job`` and return the parsed ``RouteResult``.

    Args:
        messages: Chronological chat history (latest user turn last).
        queue: ``rq.Queue`` instance (or a duck-typed stub in tests).
        poll_interval: Seconds between status polls.
        timeout: Max wait in seconds.

    Returns:
        Domain-level ``RouteResult`` — either ``kind="text"`` or
        ``kind="tool_calls"`` per ``parse_router_response``.

    Raises:
        ToolTimeoutError: Polling deadline exceeded.
        ToolJobError: Worker returned a failed status.
    """
    job = queue.enqueue(ROUTE_INTENT_JOB_REF, messages)
    assistant_message = await _await_result(job, poll_interval=poll_interval, timeout=timeout)
    return parse_router_response(assistant_message)


async def run_tool_calls_via_rq(
    *,
    calls: list[dict[str, Any]],
    queue: Any,
    poll_interval: float = _DEFAULT_POLL_INTERVAL_SEC,
    timeout: float = _DEFAULT_RUN_TIMEOUT_SEC,  # noqa: ASYNC109 — poll deadline; see _await_result
) -> dict[str, Any]:
    """Enqueue ``run_tool_calls_job`` and return ``{tool_call_id: result}``.

    An empty ``calls`` list short-circuits to ``{}`` without hitting the
    queue — saves a pointless round-trip when the LLM did not request
    any tools.

    Args:
        calls: Pickle-safe dicts consumed by the worker. Each carries
            ``tool_call_id``, ``name``, ``arguments``, and (for location
            tools) ``geolocation``.
        queue: ``rq.Queue`` instance or stub.
        poll_interval: Seconds between status polls.
        timeout: Max wait in seconds.

    Returns:
        The worker's aggregated result dict, keyed by ``tool_call_id``.
        Successful entries carry ``{"places": [...]}``; failures carry
        ``{"error": str}`` per the worker's isolation contract.

    Raises:
        ToolTimeoutError: Polling deadline exceeded.
        ToolJobError: Worker returned a failed status.
    """
    if not calls:
        return {}

    job = queue.enqueue(RUN_TOOL_CALLS_JOB_REF, calls)
    return await _await_result(job, poll_interval=poll_interval, timeout=timeout)
