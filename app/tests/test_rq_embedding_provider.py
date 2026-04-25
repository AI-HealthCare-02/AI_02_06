"""FastAPI 측 RQ 기반 EmbeddingProvider 어댑터 계약 테스트.

FastAPI는 ML 모델을 직접 로드하지 않는다. 대신 Redis Queue("ai")에
`embed_text_job`을 enqueue하고 AI-Worker가 반환한 벡터를 기다린다.
본 테스트는 어댑터의 공개 API와 동작 패턴(enqueue → wait → return)
만 락하며, 실제 RQ 처리는 별도 integration 단계에서 검증한다.
"""

import asyncio
import inspect
from typing import Any

import pytest

from app.services.rag.protocols import EmbeddingProvider
from app.services.rag.providers.rq_embedding import (
    EMBEDDING_DIMENSIONS,
    EmbeddingJobError,
    EmbeddingTimeoutError,
    RQEmbeddingProvider,
)

# ── 가짜 Job / Queue ─────────────────────────────────────────────


class _FakeJob:
    """RQ Job 모방: status / result / exc_info 3상태만 필요."""

    def __init__(self, *, result: Any = None, status: str = "queued", exc_info: str = "") -> None:
        self._result = result
        self._status = status
        self._exc_info = exc_info

    def refresh(self) -> None:
        """polling 어댑터가 호출. 기본은 no-op."""

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

    def fail(self, error: str) -> None:
        self._exc_info = error
        self._status = "failed"


class _FakeQueue:
    """rq.Queue 모방: enqueue만. 생성된 Job을 기록한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.next_job: _FakeJob | None = None

    def enqueue(self, func_ref: str, *args: Any, **kwargs: Any) -> _FakeJob:
        self.calls.append((func_ref, args, kwargs))
        job = self.next_job or _FakeJob()
        return job


# ── Tests ────────────────────────────────────────────────────────


class TestProtocolCompliance:
    """EmbeddingProvider 프로토콜 준수."""

    def test_is_embedding_provider(self) -> None:
        provider = RQEmbeddingProvider(queue=_FakeQueue())
        assert isinstance(provider, EmbeddingProvider)

    def test_dimensions_property_is_768(self) -> None:
        provider = RQEmbeddingProvider(queue=_FakeQueue())
        assert provider.dimensions == EMBEDDING_DIMENSIONS == 768

    def test_encode_single_is_async(self) -> None:
        assert inspect.iscoroutinefunction(RQEmbeddingProvider.encode_single)

    def test_encode_batch_is_async(self) -> None:
        assert inspect.iscoroutinefunction(RQEmbeddingProvider.encode_batch)


@pytest.mark.asyncio
class TestEncodeSingleDelegatesToQueue:
    """encode_single 은 Queue.enqueue 로 위임하고 결과를 대기한다."""

    async def test_enqueues_embed_text_job(self) -> None:
        queue = _FakeQueue()
        fake_vec = [0.0] * 768
        queue.next_job = _FakeJob(result=fake_vec, status="finished")

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01)
        await provider.encode_single("활명수")

        assert len(queue.calls) == 1
        func_ref, args, _kwargs = queue.calls[0]
        assert "embed_text_job" in func_ref
        assert args == ("활명수",)

    async def test_returns_job_result(self) -> None:
        queue = _FakeQueue()
        expected = [0.1] * 768
        queue.next_job = _FakeJob(result=expected, status="finished")

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01)
        result = await provider.encode_single("활명수")

        assert result == expected


@pytest.mark.asyncio
class TestEncodeSingleFailureModes:
    """실패 경로 — 타임아웃과 job 실패를 명확한 예외로 전달."""

    async def test_raises_timeout_when_never_finishes(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="queued")

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01, timeout=0.05)
        with pytest.raises(EmbeddingTimeoutError):
            await provider.encode_single("느린 쿼리")

    async def test_raises_job_failed_when_status_failed(self) -> None:
        queue = _FakeQueue()
        queue.next_job = _FakeJob(status="failed", exc_info="TraceBack")

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01, timeout=1.0)
        with pytest.raises(EmbeddingJobError):
            await provider.encode_single("깨진 쿼리")


@pytest.mark.asyncio
class TestEncodeBatchParallelism:
    """encode_batch 는 각 텍스트를 병렬 enqueue 후 순서대로 반환."""

    async def test_empty_input_returns_empty(self) -> None:
        provider = RQEmbeddingProvider(queue=_FakeQueue())
        assert await provider.encode_batch([]) == []

    async def test_multiple_texts_enqueued(self) -> None:
        queue = _FakeQueue()

        # enqueue 호출마다 즉시 완료 상태의 Job 반환
        sequence = iter([
            _FakeJob(result=[1.0] * 768, status="finished"),
            _FakeJob(result=[2.0] * 768, status="finished"),
            _FakeJob(result=[3.0] * 768, status="finished"),
        ])

        def enqueue_stub(func_ref: str, *args: Any, **_kwargs: Any) -> _FakeJob:
            queue.calls.append((func_ref, args, {}))
            return next(sequence)

        queue.enqueue = enqueue_stub  # type: ignore[method-assign]

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01)
        result = await provider.encode_batch(["a", "b", "c"])

        assert len(queue.calls) == 3
        assert result[0][0] == 1.0
        assert result[1][0] == 2.0
        assert result[2][0] == 3.0


@pytest.mark.asyncio
class TestDoesNotBlockEventLoop:
    """polling 루프가 asyncio.sleep 으로 양보하여 이벤트 루프를 막지 않는다."""

    async def test_other_tasks_can_run_during_wait(self) -> None:
        queue = _FakeQueue()
        job = _FakeJob(status="queued")
        queue.next_job = job

        async def finish_soon() -> None:
            await asyncio.sleep(0.05)
            job.finish([9.0] * 768)

        provider = RQEmbeddingProvider(queue=queue, poll_interval=0.01, timeout=2.0)
        result, _ = await asyncio.gather(
            provider.encode_single("활명수"),
            finish_soon(),
        )
        assert result[0] == 9.0
