"""
Rate Limiting Middleware

IP 기반 Rate Limiting을 전역으로 적용
- 일반 GET 요청: 느슨한 제한
- 변경 요청 (POST/PATCH/DELETE): 엄격한 제한
- 인증 엔드포인트: 가장 엄격한 제한

운영 환경에서는 Redis 기반으로 교체 권장
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate Limit 설정"""

    # 일반 GET 요청: 200 req / 60 sec per IP
    GET_MAX_REQUESTS = 200
    GET_WINDOW_SECONDS = 60

    # 변경 요청 (POST/PATCH/DELETE): 30 req / 60 sec per IP
    MUTATION_MAX_REQUESTS = 30
    MUTATION_WINDOW_SECONDS = 60

    # 인증 관련 엔드포인트: 10 req / 60 sec per IP
    AUTH_MAX_REQUESTS = 10
    AUTH_WINDOW_SECONDS = 60

    # Rate Limit 제외 경로 (헬스체크, 문서 등)
    EXCLUDED_PATHS = {
        "/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }

    # 인증 관련 경로 패턴
    AUTH_PATH_PREFIXES = {
        "/api/v1/auth/",
        "/api/v1/oauth/",
    }


class InMemoryRateLimitStore:
    """
    인메모리 Rate Limit 저장소

    주의: 다중 워커 환경에서는 각 워커의 별도 상태를 유지함
    운영 환경에서는 Redis 기반 저장소 사용 권장
    """

    def __init__(self):
        # key: (count, window_start_time)
        self._store: dict[str, tuple[int, float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5분마다 정리

    def check_and_increment(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Rate limit 체크 및 카운트 증가

        Returns:
            True: 허용
            False: 제한 초과
        """
        current_time = time.time()

        # 주기적 정리
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired(current_time)

        if key in self._store:
            count, window_start = self._store[key]

            # 윈도우 초과 시 리셋
            if current_time - window_start > window_seconds:
                self._store[key] = (1, current_time)
                return True

            # 요청 횟수 초과
            if count >= max_requests:
                return False

            self._store[key] = (count + 1, window_start)
        else:
            self._store[key] = (1, current_time)

        return True

    def _cleanup_expired(self, current_time: float) -> None:
        """만료된 항목 정리"""
        max_window = max(
            RateLimitConfig.GET_WINDOW_SECONDS,
            RateLimitConfig.MUTATION_WINDOW_SECONDS,
            RateLimitConfig.AUTH_WINDOW_SECONDS,
        )
        expired_keys = [key for key, (_, ts) in self._store.items() if current_time - ts > max_window * 2]
        for key in expired_keys:
            del self._store[key]
        self._last_cleanup = current_time


# 전역 저장소 인스턴스
_rate_limit_store = InMemoryRateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting 미들웨어"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # 제외 경로 체크
        if path in RateLimitConfig.EXCLUDED_PATHS:
            return await call_next(request)

        # 클라이언트 IP 추출
        client_ip = self._get_client_ip(request)

        # Rate limit 설정 결정
        max_requests, window_seconds = self._get_rate_limit(path, method)

        # Rate limit 체크
        rate_key = f"{client_ip}:{method}:{self._get_path_category(path)}"
        if not _rate_limit_store.check_and_increment(rate_key, max_requests, window_seconds):
            logger.warning(
                "Rate limit exceeded: ip=%s, method=%s, path=%s",
                client_ip,
                method,
                path,
            )
            return Response(
                content='{"error":"rate_limit_exceeded","error_description":"요청 횟수를 초과했습니다. 잠시 후 다시 시도해주세요."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(window_seconds)},
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출 (프록시 고려)"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 첫 번째 IP가 실제 클라이언트
            return forwarded_for.split(",")[0].strip()

        # X-Real-IP 헤더 확인 (Nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 직접 연결
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit(self, path: str, method: str) -> tuple[int, int]:
        """경로와 메서드에 따른 Rate Limit 반환"""
        # 인증 관련 경로
        for prefix in RateLimitConfig.AUTH_PATH_PREFIXES:
            if path.startswith(prefix):
                return RateLimitConfig.AUTH_MAX_REQUESTS, RateLimitConfig.AUTH_WINDOW_SECONDS

        # 변경 요청
        if method in ("POST", "PATCH", "PUT", "DELETE"):
            return RateLimitConfig.MUTATION_MAX_REQUESTS, RateLimitConfig.MUTATION_WINDOW_SECONDS

        # 일반 GET 요청
        return RateLimitConfig.GET_MAX_REQUESTS, RateLimitConfig.GET_WINDOW_SECONDS

    def _get_path_category(self, path: str) -> str:
        """경로 카테고리 반환 (Rate limit 키 생성용)"""
        for prefix in RateLimitConfig.AUTH_PATH_PREFIXES:
            if path.startswith(prefix):
                return "auth"
        return "api"
