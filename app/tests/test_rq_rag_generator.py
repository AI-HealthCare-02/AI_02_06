"""FastAPI 측 RQ 기반 RAGGenerator 어댑터 계약 테스트.

``RQEmbeddingProvider`` 와 대칭되는 LLM 전용 어댑터. FastAPI 프로세스는
OpenAI 클라이언트를 만들지 않고 Redis Queue("ai") 에 두 개의 LLM job 을
enqueue 한다. 어댑터는 기존 ``RAGGenerator`` 의 공개 메서드 시그니처
(``rewrite_query``, ``generate_chat_response``) 를 그대로 보존하여
``RAGPipeline`` 재배선 없이 교체 가능하도록 한다.
"""

import asyncio
import inspect
from typing import Any

import pytest

from app.dtos.rag import ChatCompletion, RewriteResult, RewriteStatus, TokenUsage
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
    """RAGGenerator 의 공개 메서드 시그니처를 준수해야 RAGPipeline 호환."""

    def test_rewrite_query_is_async(self) -> None:
        assert inspect.iscoroutinefunction(RQRAGGenerator.rewrite_query)

    def test_generate_chat_response_is_async(self) -> None:
        assert inspect.iscoroutinefunction(RQRAGGenerator.generate_chat_response)

    def test_rewrite_query_signature(self) -> None:
        sig = inspect.signature(RQRAGGenerator.rewrite_query)
        params = set(sig.parameters.keys())
        assert "history" in params
        assert "current_query" in params

    def test_generate_chat_response_signature(self) -> None:
        sig = inspect.signature(RQRAGGenerator.generate_chat_response)
        params = set(sig.parameters.keys())
        assert "messages" in params
        assert "system_prompt" in params


@pytest.mark.asyncio
class TestRewriteQueryRoundtrip:
    """rewrite_query 는 rewrite_query_job 을 enqueue하고 dict 결과를 RewriteResult로 승격한다."""

    async def test_enqueues_rewrite_job(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={"status": "ok", "query": "활명수의 효능", "token_usage": None},
            status="finished",
        )
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        await gen.rewrite_query(history=[], current_query="활명수 효능 알려줘")

        func_ref, args, _kwargs = queue.calls[0]
        assert "rewrite_query_job" in func_ref
        assert args == ([], "활명수 효능 알려줘")

    async def test_returns_rewrite_result_ok(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={
                "status": "ok",
                "query": "활명수의 효능",
                "token_usage": {
                    "model": "gpt-4o-mini",
                    "prompt_tokens": 230,
                    "completion_tokens": 10,
                    "total_tokens": 240,
                },
            },
            status="finished",
        )
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        result = await gen.rewrite_query(history=[], current_query="x")

        assert isinstance(result, RewriteResult)
        assert result.status == RewriteStatus.OK
        assert result.query == "활명수의 효능"
        assert isinstance(result.token_usage, TokenUsage)
        assert result.token_usage.total_tokens == 240

    async def test_returns_rewrite_result_unresolvable(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(
            result={"status": "unresolvable", "query": "원본", "token_usage": None},
            status="finished",
        )
        gen = RQRAGGenerator(queue=queue, poll_interval=0.01, timeout=1.0)

        result = await gen.rewrite_query(history=[], current_query="원본")
        assert result.status == RewriteStatus.UNRESOLVABLE


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
                    "model": "gpt-4o-mini",
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
            await gen.rewrite_query(history=[], current_query="x")

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
