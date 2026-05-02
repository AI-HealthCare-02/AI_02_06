"""자체 retry decorator — tenacity 외부 의존 없이 ~50 라인.

PLAN.md (feature/RAG) §4 D1 결정 — tenacity 가 아닌 자체 구현 채택.

정책:
- max_attempts=2 (기본). 즉 첫 호출 + 1회 재시도 = 총 2회.
- exponential backoff: 0.5s → 1.0s (max 1초). 누적 max wait < 1.5s.
- retryable: ConnectionError, TimeoutError, OpenAI/Kakao 의 일시적 5xx.
- non-retryable: ValueError, TypeError, OpenAI BadRequestError (4xx) 즉시 raise.
- async/sync 자동 분기.

본 PR 의 적용 대상: ai_worker.tool_calling.jobs._dispatch 내부 외부 호출
(Kakao API, OpenAI Embedding API). RAG retrieval 자체는 DB 라 retry 불필요.
"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def retry_async(
    *,
    max_attempts: int = 2,
    initial_backoff: float = 0.5,
    max_backoff: float = 1.0,
    retryable: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """비동기 함수를 retry 로 감싸는 decorator factory.

    Args:
        max_attempts: 최대 호출 횟수 (재시도 + 첫 호출). 기본 2.
        initial_backoff: 첫 재시도 전 대기 (초). 기본 0.5.
        max_backoff: 누적 backoff 상한 (초). 기본 1.0.
        retryable: 재시도 대상 예외 클래스 tuple. 다른 예외는 즉시 raise.

    Returns:
        decorated async function. 모든 시도 실패 시 마지막 예외 propagate.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현. Phase 3 에서 채움.
    """
    del max_attempts, initial_backoff, max_backoff, retryable

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        del func
        msg = "retry_async 는 Phase 3 [Implement] 에서 채움"
        raise NotImplementedError(msg)

    return decorator
