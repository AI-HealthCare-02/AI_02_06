"""
보안 검증 타입

Pydantic 모델에서 재사용 가능한 보안 타입 정의
사용법: str 대신 SafeString, CleanString 등을 타입으로 지정
"""

import re
from typing import Annotated

import bleach
from pydantic import AfterValidator, BeforeValidator

# 위험한 패턴 목록 (SQL Injection, XSS, Template Injection, Path Traversal)
DANGEROUS_PATTERNS = [
    # XSS
    (r"<script", "스크립트 태그"),
    (r"javascript:", "자바스크립트 프로토콜"),
    (r"on\w+\s*=", "이벤트 핸들러"),
    (r"<iframe", "iframe 태그"),
    # SQL Injection
    (r"'\s*OR\s+", "SQL OR 구문"),
    (r'"\s*OR\s+', "SQL OR 구문"),
    (r";\s*DROP\s+", "SQL DROP 구문"),
    (r";\s*DELETE\s+", "SQL DELETE 구문"),
    (r"UNION\s+SELECT", "SQL UNION 구문"),
    (r"--\s*$", "SQL 주석"),
    # Template Injection
    (r"\{\{", "템플릿 구문"),
    (r"\$\{", "템플릿 구문"),
    (r"#\{", "템플릿 구문"),
    # Path Traversal
    (r"\.\.[/\\]", "경로 탐색"),
]


def check_dangerous_patterns(value: str) -> str:
    """위험한 패턴 검사 (발견 시 ValueError)"""
    if not isinstance(value, str):
        return value

    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValueError(f"허용되지 않는 입력입니다: {description}")
    return value


def sanitize_html(value: str) -> str:
    """HTML 태그 완전 제거"""
    if not isinstance(value, str):
        return value
    return bleach.clean(value, tags=[], strip=True)


def sanitize_html_partial(value: str) -> str:
    """안전한 HTML 태그만 허용 (b, i, u, p, br)"""
    if not isinstance(value, str):
        return value
    allowed_tags = ["b", "i", "u", "p", "br", "strong", "em"]
    return bleach.clean(value, tags=allowed_tags, strip=True)


def strip_whitespace(value: str) -> str:
    """앞뒤 공백 제거"""
    if not isinstance(value, str):
        return value
    return value.strip()


# 재사용 가능한 타입 정의
# 사용 예: nickname: SafeString

# 위험 패턴 차단 (XSS, SQLi 등)
SafeString = Annotated[str, AfterValidator(check_dangerous_patterns)]

# HTML 완전 제거 + 공백 정리
CleanString = Annotated[
    str,
    BeforeValidator(strip_whitespace),
    AfterValidator(sanitize_html),
    AfterValidator(check_dangerous_patterns),
]

# 일부 HTML 허용 (채팅 등)
PartialHtmlString = Annotated[
    str,
    BeforeValidator(strip_whitespace),
    AfterValidator(sanitize_html_partial),
    AfterValidator(check_dangerous_patterns),
]

# 공백만 정리 (위험 패턴 검사 없음, 신뢰된 내부 데이터용)
TrimmedString = Annotated[str, BeforeValidator(strip_whitespace)]
