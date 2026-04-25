"""RQ 기반 EmbeddingProvider 어댑터 (FastAPI 측).

FastAPI 프로세스는 임베딩 모델을 직접 로드하지 않는다. 대신 Redis
Queue("ai") 에 `embed_text_job` 호출을 enqueue하고 AI-Worker가 반환한
벡터를 기다린다. 본 어댑터는 기존 ``EmbeddingProvider`` 프로토콜을
그대로 준수하므로 ``RAGPipeline`` 구성 코드는 수정할 필요가 없다.

Phase X-3 구현 범위:
- ``encode_single`` / ``encode_batch`` 두 메서드가 RQ enqueue로 위임.
- 결과 대기는 ``asyncio.sleep`` 폴링으로 이벤트 루프 비블로킹 보장.
- 타임아웃과 job 실패를 전용 예외로 승격.

FastAPI 쪽에서 ML 상주 메모리를 들고 있던 과거 구현
(``sentence_transformer.SentenceTransformerProvider``)은 본 어댑터가
RAG 파이프라인에 주입되는 순간 사용되지 않는다. 실제 교체 스위치는
``app/services/rag/__init__.py`` 에서 이루어진다 (Phase X-3 후반).
"""

import asyncio
import time
from typing import Any

# Queue 타입 힌트용만 import — 실제 인스턴스는 외부 주입 (테스트 용이성).
try:
    from rq import Queue  # pragma: no cover — type hint only
except ImportError:  # pragma: no cover
    Queue = Any  # type: ignore[misc, assignment]


EMBEDDING_DIMENSIONS = 768
_DEFAULT_POLL_INTERVAL_SEC = 0.1
_DEFAULT_TIMEOUT_SEC = 30.0
_EMBED_JOB_REF = "ai_worker.tasks.rag_tasks.embed_text_job"


class EmbeddingTimeoutError(TimeoutError):
    """RQ job 이 timeout 내 완료되지 않았을 때."""


class EmbeddingJobError(RuntimeError):
    """RQ job 이 실패 상태로 종료됐을 때."""


class RQEmbeddingProvider:
    """Embedding calls backed by an RQ queue.

    The provider implements ``EmbeddingProvider`` protocol by enqueuing
    ``embed_text_job`` and polling for completion via ``asyncio.sleep``
    so the FastAPI event loop is never blocked.

    Attributes:
        queue: ``rq.Queue`` instance bound to the "ai" queue.
        poll_interval: Seconds between status polls.
        timeout: Max wait in seconds before raising ``EmbeddingTimeoutError``.
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

    @property
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
        return EMBEDDING_DIMENSIONS

    async def encode_single(self, text: str) -> list[float]:
        """Enqueue a single embed job and await its result.

        Args:
            text: Query text to embed.

        Returns:
            768-dim L2-normalised embedding produced by AI-Worker.

        Raises:
            EmbeddingTimeoutError: If the job does not finish within timeout.
            EmbeddingJobError: If AI-Worker reports a failed status.
        """
        job = self._queue.enqueue(_EMBED_JOB_REF, text)
        return await self._await_result(job)

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts concurrently via independent RQ jobs.

        Args:
            texts: List of inputs.

        Returns:
            Vectors in the same order as ``texts``.
        """
        if not texts:
            return []

        jobs = [self._queue.enqueue(_EMBED_JOB_REF, t) for t in texts]
        waits = [self._await_result(j) for j in jobs]
        return await asyncio.gather(*waits)

    # ── Internals ────────────────────────────────────────────────

    async def _await_result(self, job: Any) -> list[float]:
        """Poll a Job until it finishes, fails, or we exceed the timeout."""
        deadline = time.monotonic() + self._timeout

        while True:
            job.refresh()
            status = job.get_status()

            if status == "finished":
                return job.result

            if status == "failed":
                raise EmbeddingJobError(job.exc_info or "AI-Worker embedding failed")

            if time.monotonic() >= deadline:
                raise EmbeddingTimeoutError(f"Embedding job did not finish within {self._timeout}s")

            await asyncio.sleep(self._poll_interval)
