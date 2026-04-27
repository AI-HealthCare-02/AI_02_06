"""OCR 텍스트 후처리 — 약품명 후보 추출.

CLOVA OCR 응답 원문에서 복용 지시·날짜·용량 등 비약품명 텍스트를 제거하고
약품명일 가능성이 높은 토큰만 추려낸다.

흐름: clean_ocr_text(raw) -> str  (정규식·블랙리스트 적용)
       extract_medicine_candidates(cleaned) -> list[str]
"""

import logging
import re

logger = logging.getLogger(__name__)


_REMOVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+일\s*\d+회"),
    re.compile(r"식(전|후)\s*\d+분?"),
    re.compile(r"\d+일분"),
    re.compile(r"\d+(정|캡슐|ml|mg|g|포|T|C)"),
    re.compile(r"(아침|점심|저녁|취침)\s*(전|후)?"),
    re.compile(r"\d+\s*일\s*분"),
    re.compile(r"(매일|격일|필요\s*시)"),
    re.compile(r"\d{4}[-/.]\d{2}[-/.]\d{2}"),
    re.compile(r"(조제|처방)\s*일\s*:?\s*\S+"),
]

_BLACKLIST_KEYWORDS: list[str] = [
    "용량",
    "용법",
    "처방",
    "조제",
    "약국",
    "의원",
    "병원",
    "클리닉",
    "의료",
    "전화",
    "주소",
    "원장",
    "약사",
    "복약안내",
    "복용방법",
    "주의사항",
    "유효기간",
    "환자",
    "성명",
    "연락처",
    "접수",
    "수납",
    "영수",
]

_MIN_NAME_LENGTH = 2
_NUMERIC_ONLY_PATTERN = re.compile(r"\d+")


def clean_ocr_text(raw_text: str) -> str:
    """OCR 원문에서 복용지시·날짜·특수문자 노이즈를 제거한다.

    Args:
        raw_text: CLOVA OCR 가 반환한 원문 텍스트.

    Returns:
        정규식·특수문자 정리·공백 정규화가 적용된 문자열.
    """
    cleaned = raw_text.strip()
    for pattern in _REMOVE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"[^\w\s\(\)\-]", " ", cleaned)
    return " ".join(cleaned.split())


def extract_medicine_candidates(cleaned_text: str) -> list[str]:
    """정리된 텍스트에서 약품명 후보 토큰만 추려 반환한다.

    Args:
        cleaned_text: ``clean_ocr_text`` 가 거른 텍스트.

    Returns:
        약품명일 가능성이 있는 토큰 리스트 (짧음·블랙리스트·숫자 제외).
    """
    candidates = [token for token in cleaned_text.split() if _is_candidate(token)]
    logger.info("Extracted %d medicine candidates from OCR text", len(candidates))
    return candidates


def _is_candidate(token: str) -> bool:
    """약품명 후보 자격 검증 (길이·블랙리스트·숫자 only 컷)."""
    stripped = token.strip()
    if len(stripped) < _MIN_NAME_LENGTH:
        return False
    if _NUMERIC_ONLY_PATTERN.fullmatch(stripped):
        return False
    return not _is_blacklisted(stripped)


def _is_blacklisted(token: str) -> bool:
    """블랙리스트 키워드 포함 여부."""
    return any(keyword in token for keyword in _BLACKLIST_KEYWORDS)
