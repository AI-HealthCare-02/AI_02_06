"""
Rate Limiting 서비스

현재: 인메모리 기반 (단일 워커용)
운영: Redis 기반으로 교체 권장
"""

import time
from abc import ABC, abstractmethod

from fastapi import HTTPException, status


class RateLimiter(ABC):
    """Rate Limiter 인터페이스"""

    @abstractmethod
    def check(self, key: str) -> None:
        """Rate limit 체크. 초과 시 HTTPException 발생"""
        pass


class InMemoryRateLimiter(RateLimiter):
    """
    인메모리 기반 Rate Limiter

    주의: 다중 워커 환경에서는 각 워커가 별도 상태를 유지함
    운영 환경에서는 RedisRateLimiter 사용 권장
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._tracker: dict[str, tuple[int, float]] = {}

    def check(self, key: str) -> None:
        current_time = time.time()

        if key in self._tracker:
            count, timestamp = self._tracker[key]

            # 윈도우 초과 시 리셋
            if current_time - timestamp > self.window_seconds:
                self._tracker[key] = (1, current_time)
                return

            # 요청 횟수 초과
            if count >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "error_description": f"요청 횟수를 초과했습니다. {self.window_seconds}초 후에 다시 시도해주세요.",
                    },
                )

            self._tracker[key] = (count + 1, timestamp)
        else:
            self._tracker[key] = (1, current_time)


# 기본 인스턴스 (DI용)
default_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)


def get_rate_limiter() -> RateLimiter:
    """Rate Limiter 의존성"""
    return default_rate_limiter
