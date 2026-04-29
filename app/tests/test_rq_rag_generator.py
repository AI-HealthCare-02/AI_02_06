"""FastAPI 측 RQ 기반 LLM 어댑터 계약 테스트 (옵션 C 이후 잔여).

옵션 C 에서 ``rewrite_query`` 가 폐기됐으므로 본 파일은 ``generate_chat_response``
와 실패 모드 / 비차단 폴링만 검증한다. ``summarize_messages`` 는 별도의
session_compact_service 테스트에서 통합 검증된다.
"""

import asyncio
import inspect
from typing import Any

import pytest

from app.dtos.rag import ChatCompletion, TokenUsage
from app.services.rag.providers.rq_llm import (
    LLMJobError,
    LLMTimeoutError,
    RQRAGGenerator,
)

# ── 가짜 Job / Queue ────────────────────────────────────────────


class _FakeJob:
    def __init__(self, *, result: Any = None, status: str = "queued", exc_info: str = "") -> None:
        self._result = result
        self._status = status
        self._exc_info = exc_info

    def refresh(self) -> None:
        """Default no-op; test-specific subclass or monkeypatch overrides."""

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
        return self.next_job or _FakeJob()


# ── Tests ───────────────────────────────────────────────────────


class TestApiShape:
    """RQRAGGenerator 의 공개 메서드 시그니처."""

    def test_generate_chat_response_is_async(self) -> None:
        assert inspect.iscoroutinefunction(RQRAGGenerator.generate_chat_response)

    def test_generate_chat_response_signature(self) -> None:
        sig = inspect.signature(RQRAGGenerator.generate_chat_response)
        params = set(sig.parameters.keys())
        assert "messages" in params
        assert "system_prompt" in params


@pytest.mark.asyncio
class TestGenerateChatResponseRoundtrip:
    """generate_chat_response 는 generate_chat_response_job 을 enqueue한다."""

    async def test_enqueues_generate_job(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={"answer": "활명수는 소화제입니다.", "token_usage": None},
            status="finished",
        )
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        await gen.generate_chat_response(
            messages=[{"role": "user", "content": "q"}],
            system_prompt="system",
        )

        func_ref, args, _kwargs = queue.calls[0]
        assert "generate_chat_response_job" in func_ref
        assert args[0] == [{"role": "user", "content": "q"}]
        assert args[1] == "system"

    async def test_returns_chat_completion(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={
                "answer": "활명수는 소화제입니다.",
                "token_usage": {
                    "model": "gpt-4o",
                    "prompt_tokens": 800,
                    "completion_tokens": 80,
                    "total_tokens": 880,
                },
            },
            status="finished",
        )
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        result = await gen.generate_chat_response(messages=[], system_prompt=None)

        assert isinstance(result, ChatCompletion)
        assert result.answer == "활명수는 소화제입니다."
        assert isinstance(result.token_usage, TokenUsage)
        assert result.token_usage.total_tokens == 880


@pytest.mark.asyncio
class TestFailureModes:
    async def test_timeout_raises(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="queued")
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=0.05)

        with pytest.raises(LLMTimeoutError):
            await gen.generate_chat_response(messages=[], system_prompt=None)

    async def test_failed_status_raises(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="failed", exc_info="Traceback...")
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        with pytest.raises(LLMJobError):
            await gen.generate_chat_response(messages=[], system_prompt=None)


@pytest.mark.asyncio
class TestNonBlockingPolling:
    async def test_other_tasks_can_run_while_waiting(self) -> None:
        queue = _FakeQueue()
        job = _FakeJob(status="queued")
        queue.next_job = job

        async def finish_soon() -> None:
            await asyncio.sleep(0.05)
            job.finish({"answer": "ok", "token_usage": None})

        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=2.0)
        result, _ = await asyncio.gather(
            gen.generate_chat_response(messages=[], system_prompt=None),
            finish_soon(),
        )
        assert result.answer == "ok"
