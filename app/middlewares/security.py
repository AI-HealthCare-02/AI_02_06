"""
Security Middleware

1. 입력값 검증 (1차 방어 - 명백한 공격 패턴 차단)
2. CSP 헤더 추가 (nonce 기반, unsafe-inline 불허)
3. 보안 헤더 추가 (X-Frame-Options, X-Content-Type-Options 등)
"""

import re
import secrets
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# 명백한 공격 패턴 (1차 방어, Middleware에서 차단)
ATTACK_PATTERNS = [
    # SQL Injection (명백한 패턴만)
    r"('\s*OR\s+'?\s*'?\s*=|'\s*OR\s+1\s*=\s*1)",
    r'("\s*OR\s+"?\s*"?\s*=|"\s*OR\s+1\s*=\s*1)',
    r";\s*(DROP|DELETE|UPDATE|INSERT)\s+",
    r"UNION\s+(ALL\s+)?SELECT",
    # Path Traversal
    r"\.\.[/\\]",
    r"\.\.%2[fF]",
    # Null Byte Injection
    r"%00",
    r"\x00",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ATTACK_PATTERNS]


def contains_attack_pattern(value: str) -> bool:
    """공격 패턴 포함 여부 검사"""
    for pattern in COMPILED_PATTERNS:
        if pattern.search(value):
            return True
    return False


def check_request_params(request: Request) -> str | None:
    """요청 파라미터에서 공격 패턴 검사"""
    # Query Parameters
    for key, value in request.query_params.items():
        if contains_attack_pattern(key) or contains_attack_pattern(value):
            return f"query:{key}"

    # Path Parameters
    for key, value in request.path_params.items():
        if isinstance(value, str) and contains_attack_pattern(value):
            return f"path:{key}"

    return None


class SecurityMiddleware(BaseHTTPMiddleware):
    """보안 미들웨어"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. 입력값 검증 (Query, Path만 - Body는 Pydantic에서 처리)
        attack_param = check_request_params(request)
        if attack_param:
            return Response(
                content='{"detail":{"error":"invalid_input","error_description":"허용되지 않는 입력입니다."}}',
                status_code=400,
                media_type="application/json",
            )

        # 2. 요청 처리
        response = await call_next(request)

        # 3. 보안 헤더 추가
        self._add_security_headers(request, response)

        return response

    def _add_security_headers(self, request: Request, response: Response) -> None:
        """보안 헤더 추가"""
        # nonce 생성 (CSP용)
        nonce = secrets.token_urlsafe(16)

        # CSP 헤더 (unsafe-inline 불허)
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            f"style-src 'self' 'nonce-{nonce}'",
            "img-src 'self' https://k.kakaocdn.net data: blob:",
            "font-src 'self'",
            "connect-src 'self' https://kauth.kakao.com https://kapi.kakao.com",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # 기타 보안 헤더
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # nonce를 request state에 저장 (템플릿에서 사용 가능)
        request.state.csp_nonce = nonce
