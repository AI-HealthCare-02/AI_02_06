"""Tool calling RQ 어댑터 계약 테스트 (Y-6 Red).

FastAPI 측에서 AI-Worker 의 두 job 을 큐잉 → 결과를 기다리는 어댑터.
RAG 의 ``RQEmbeddingProvider`` 와 동일한 poll-loop 패턴을 따른다.

- ``route_intent_via_rq(messages, queue)`` -> ``RouteResult``
- ``run_tool_calls_via_rq(calls, queue)`` -> ``dict`` (tool_call_id → result)

Red 전제:
- 두 함수는 async.
- timeout / job failed 는 전용 예외 ``ToolTimeoutError`` / ``ToolJobError``.
"""

import asyncio
import inspect
from typing import Any

import pytest

from app.dtos.tools import RouteResult
from app.services.tools.rq_adapters import (
    ROUTE_INTENT_JOB_REF,
    RUN_TOOL_CALLS_JOB_REF,
    ToolJobError,
    ToolTimeoutError,
    route_intent_via_rq,
    run_tool_calls_via_rq,
)


class _FakeJob:
    def __init__(self, *, result: Any = None, status: str = "queued", exc_info: str = "") -> None:
        self._result = result
        self._status = status
        self._exc_info = exc_info

    def refresh(self) -> None:
        """polling 시 호출."""

    def get_status(self) -> str:
        return self._status

    @property
    def result(self) -> Any:
        return self._result

    @property
    def exc_info(self) -> str:
        return self._exc_info

    def finish(self, value: Any) -> None:
        self._result = value
        self._status = "finished"


class _FakeQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.next_job: _FakeJob | None = None

    def enqueue(self, func_ref: str, *args: Any, **kwargs: Any) -> _FakeJob:
        self.calls.append((func_ref, args, kwargs))
        job = self.next_job or _FakeJob()
        return job


# ── Signatures ────────────────────────────────────────────────


class TestSignatures:
    def test_route_is_async(self) -> None:
        assert inspect.iscoroutinefunction(route_intent_via_rq)

    def test_run_is_async(self) -> None:
        assert inspect.iscoroutinefunction(run_tool_calls_via_rq)


# ── route_intent_via_rq ───────────────────────────────────────


class TestRouteIntentViaRq:
    @pytest.mark.asyncio
    async def test_enqueues_route_intent_job_with_messages(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={
                "role": "assistant",
                "content": "안녕하세요",
                "tool_calls": None,
            },
            status="finished",
        )

        msgs = [{"role": "user", "content": "안녕"}]
        result = await route_intent_via_rq(messages=msgs, queue=queue, poll_interval=0.01)

        assert len(queue.calls) == 1
        func_ref, args, _kwargs = queue.calls[0]
        assert func_ref == ROUTE_INTENT_JOB_REF
        assert args == (msgs,)

        assert isinstance(result, RouteResult)
        assert result.kind == "text"
        assert result.text == "안녕하세요"

    @pytest.mark.asyncio
    async def test_parses_tool_calls_response(self) -> None:
        import json

        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "search_hospitals_by_keyword",
                            "arguments": json.dumps({"query": "강남역 약국"}),
                        },
                    },
                ],
            },
            status="finished",
        )

        result = await route_intent_via_rq(
            messages=[{"role": "user", "content": "강남역 약국"}],
            queue=queue,
            poll_interval=0.01,
        )
        assert result.kind == "tool_calls"
        assert result.tool_calls[0].name == "search_hospitals_by_keyword"

    @pytest.mark.asyncio
    async def test_raises_timeout_when_never_finishes(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="queued")

        with pytest.raises(ToolTimeoutError):
            await route_intent_via_rq(
                messages=[{"role": "user", "content": "x"}],
                queue=queue,
                poll_interval=0.01,
                timeout=0.05,
            )

    @pytest.mark.asyncio
    async def test_raises_job_error_on_failure(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="failed", exc_info="boom")

        with pytest.raises(ToolJobError):
            await route_intent_via_rq(
                messages=[{"role": "user", "content": "x"}],
                queue=queue,
                poll_interval=0.01,
                timeout=1.0,
            )


# ── run_tool_calls_via_rq ────────────────────────────────────


class TestRunToolCallsViaRq:
    @pytest.mark.asyncio
    async def test_enqueues_run_tool_calls_job(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(result={"c1": {"places": []}}, status="finished")

        calls = [{"tool_call_id": "c1", "name": "search_hospitals_by_keyword", "arguments": {"query": "x"}}]
        result = await run_tool_calls_via_rq(calls=calls, queue=queue, poll_interval=0.01)

        func_ref, args, _kwargs = queue.calls[0]
        assert func_ref == RUN_TOOL_CALLS_JOB_REF
        assert args == (calls,)
        assert result == {"c1": {"places": []}}

    @pytest.mark.asyncio
    async def test_empty_calls_returns_empty_dict_without_enqueue(self) -> None:
        queue = _FakeQueue()

        result = await run_tool_calls_via_rq(calls=[], queue=queue, poll_interval=0.01)

        assert result == {}
        assert queue.calls == []

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="queued")

        with pytest.raises(ToolTimeoutError):
            await run_tool_calls_via_rq(
                calls=[{"tool_call_id": "c1", "name": "x", "arguments": {}}],
                queue=queue,
                poll_interval=0.01,
                timeout=0.05,
            )


class TestDoesNotBlockLoop:
    @pytest.mark.asyncio
    async def test_other_tasks_can_run_while_waiting(self) -> None:
        queue = _FakeQueue()
        job = _FakeJob(status="queued")
        queue.next_job = job

        async def finish_soon() -> None:
            await asyncio.sleep(0.05)
            job.finish({"role": "assistant", "content": "late", "tool_calls": None})

        result, _ = await asyncio.gather(
            route_intent_via_rq(
                messages=[{"role": "user", "content": "x"}],
                queue=queue,
                poll_interval=0.01,
                timeout=2.0,
            ),
            finish_soon(),
        )
        assert result.kind == "text"
        assert result.text == "late"
