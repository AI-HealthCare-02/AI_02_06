"""
Security Middleware

1. 입력값 검증 (로깅 + 명백한 공격만 차단, ORM이 주요 방어)
2. 보안 헤더 추가 (X-Frame-Options, X-Content-Type-Options 등)

Note: CSP는 Next.js SPA와 호환성 문제로 FE에서 설정 권장
"""

import logging
import re
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 명백한 공격 패턴 (로깅 + 차단)
ATTACK_PATTERNS = [
    # Path Traversal (명확한 공격)
    (r"\.\.[/\\]", "path_traversal"),
    (r"\.\.%2[fF]", "path_traversal_encoded"),
    # Null Byte Injection (명확한 공격)
    (r"%00", "null_byte"),
    (r"\x00", "null_byte"),
]

# 의심 패턴 (로깅만, 차단 안 함 - ORM이 방어)
SUSPICIOUS_PATTERNS = [
    (r"('\s*OR\s+'?\s*'?\s*=|'\s*OR\s+1\s*=\s*1)", "sql_injection_suspect"),
    (r'("\s*OR\s+"?\s*"?\s*=|"\s*OR\s+1\s*=\s*1)', "sql_injection_suspect"),
    (r";\s*(DROP|DELETE|UPDATE|INSERT)\s+", "sql_injection_suspect"),
    (r"UNION\s+(ALL\s+)?SELECT", "sql_union_suspect"),
    (r"<script", "xss_suspect"),
    (r"javascript:", "xss_suspect"),
]

COMPILED_ATTACK_PATTERNS = [(re.compile(p, re.IGNORECASE), name) for p, name in ATTACK_PATTERNS]
COMPILED_SUSPICIOUS_PATTERNS = [(re.compile(p, re.IGNORECASE), name) for p, name in SUSPICIOUS_PATTERNS]


def check_attack_patterns(value: str) -> str | None:
    """명백한 공격 패턴 검사 (차단 대상)"""
    for pattern, name in COMPILED_ATTACK_PATTERNS:
        if pattern.search(value):
            return name
    return None


def check_suspicious_patterns(value: str) -> str | None:
    """의심 패턴 검사 (로깅만)"""
    for pattern, name in COMPILED_SUSPICIOUS_PATTERNS:
        if pattern.search(value):
            return name
    return None


def scan_request_params(request: Request) -> tuple[str | None, str | None]:
    """
    요청 파라미터 검사

    Returns:
        (공격 패턴, 의심 패턴) - 발견 시 패턴 이름, 없으면 None
    """
    attack_found = None
    suspicious_found = None

    # Query Parameters
    for key, value in request.query_params.items():
        for v in [key, value]:
            if not attack_found:
                attack_found = check_attack_patterns(v)
            if not suspicious_found:
                suspicious_found = check_suspicious_patterns(v)

    # Path Parameters
    for _key, value in request.path_params.items():
        if isinstance(value, str):
            if not attack_found:
                attack_found = check_attack_patterns(value)
            if not suspicious_found:
                suspicious_found = check_suspicious_patterns(value)

    return attack_found, suspicious_found


class SecurityMiddleware(BaseHTTPMiddleware):
    """보안 미들웨어"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. 입력값 검사
        attack_pattern, suspicious_pattern = scan_request_params(request)

        # 의심 패턴 로깅 (차단 안 함)
        if suspicious_pattern:
            logger.warning(
                "Suspicious pattern detected: %s, path=%s, ip=%s",
                suspicious_pattern,
                request.url.path,
                request.client.host if request.client else "unknown",
            )

        # 명백한 공격 패턴 차단
        if attack_pattern:
            logger.error(
                "Attack pattern blocked: %s, path=%s, ip=%s",
                attack_pattern,
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            return Response(
                content='{"detail":{"error":"invalid_input","error_description":"허용되지 않는 입력입니다."}}',
                status_code=400,
                media_type="application/json",
            )

        # 2. 요청 처리
        response = await call_next(request)

        # 3. 보안 헤더 추가
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """보안 헤더 추가 (CSP 제외 - SPA 호환성)"""
        # 기본 보안 헤더
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP는 Next.js에서 설정 (next.config.js의 headers())
        # SPA의 인라인 스크립트와 호환성 문제로 BE에서 제외
