"""Unit tests for app.services.tools.retry — 자체 구현 retry decorator (D1).

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 실 동작 검증으로 전환.

PLAN.md (feature/RAG) §4.1 Step 2 — retry helper 의 4가지 의도된 동작:
- 일시적 ConnectionError 1회 후 성공 → 호출 2번 (재시도 1회)
- 2회 모두 실패 → 마지막 예외 propagate
- ValueError 같은 non-retryable → retry 안함, 즉시 raise
- exponential backoff 누적 max wait < 1.5s
"""

from __future__ import annotations

import pytest

from app.services.tools.retry import retry_async


class TestRetryAsync:
    """retry_async decorator factory 단위 테스트 (Red 상태)."""

    @pytest.mark.asyncio
    async def test_retry_once_then_success(self) -> None:
        """일시적 ConnectionError 1회 후 성공 → 호출 2번."""
        call_count = 0

        with pytest.raises(NotImplementedError):  # noqa: PT012

            @retry_async(max_attempts=2)
            async def _flaky() -> str:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("transient")
                return "ok"

            await _flaky()

    @pytest.mark.asyncio
    async def test_all_attempts_fail_propagate(self) -> None:
        """max_attempts 모두 ConnectionError → 마지막 예외 propagate."""
        with pytest.raises(NotImplementedError):  # noqa: PT012

            @retry_async(max_attempts=2)
            async def _always_fail() -> None:
                raise ConnectionError("permanent")

            await _always_fail()

    @pytest.mark.asyncio
    async def test_non_retryable_immediate_raise(self) -> None:
        """ValueError 는 retryable 에 없음 → retry 안함, 즉시 raise."""
        with pytest.raises(NotImplementedError):  # noqa: PT012

            @retry_async(max_attempts=3)
            async def _bad_input() -> None:
                raise ValueError("invalid")

            await _bad_input()

    @pytest.mark.asyncio
    async def test_decorator_factory_returns_callable(self) -> None:
        """decorator factory 자체가 callable 반환 — stub 단계에선 NotImplementedError."""
        with pytest.raises(NotImplementedError):

            @retry_async()
            async def _noop() -> None:
                return None
