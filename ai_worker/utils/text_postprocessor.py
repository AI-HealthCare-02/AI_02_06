"""OCR text postprocessing module.

This module provides text cleaning and filtering functions
to extract medicine name candidates from raw OCR output
by removing dosage instructions, irrelevant keywords,
and normalizing text formatting.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── 제거 대상 정규식 (복용 지시, 날짜, 용량 등 비약품명 텍스트) ──────
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

# ── 블랙리스트 키워드 (약국/병원/환자 정보 등 비약품명 단어) ─────────
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

# Minimum length for a valid medicine name candidate
_MIN_NAME_LENGTH = 2


# ── 텍스트 클리닝 (정규식 제거 -> 특수문자 제거 -> 공백 정규화) ──────


def clean_ocr_text(raw_text: str) -> str:
    """Remove dosage instructions and noise from raw OCR text.

    Applies regex pattern removal, blacklist filtering,
    and whitespace normalization to clean OCR output.

    Args:
        raw_text: Raw text string extracted from CLOVA OCR.

    Returns:
        Cleaned text with dosage/instruction noise removed.
    """
    cleaned = raw_text.strip()

    for pattern in _REMOVE_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    cleaned = re.sub(r"[^\w\s\(\)\-]", " ", cleaned)
    cleaned = " ".join(cleaned.split())

    return cleaned


# ── 약품명 후보 추출 (토큰 분리 -> 블랙리스트/숫자 제외 -> 후보 반환) ──


def extract_medicine_candidates(cleaned_text: str) -> list[str]:
    """Extract potential medicine name tokens from cleaned text.

    Splits cleaned OCR text into tokens and filters out
    blacklisted keywords and short fragments that are
    unlikely to be medicine names.

    Args:
        cleaned_text: Text after clean_ocr_text processing.

    Returns:
        List of medicine name candidate strings.
    """
    tokens = cleaned_text.split()
    candidates: list[str] = []

    for token in tokens:
        token = token.strip()

        if len(token) < _MIN_NAME_LENGTH:
            continue

        if _is_blacklisted(token):
            continue

        if re.fullmatch(r"\d+", token):
            continue

        candidates.append(token)

    logger.info(
        "Extracted %d medicine candidates from OCR text",
        len(candidates),
    )
    return candidates


# ── 블랙리스트 판별 헬퍼 ─────────────────────────────────────────────


def _is_blacklisted(token: str) -> bool:
    """Check if a token matches any blacklist keyword.

    Args:
        token: Text token to check.

    Returns:
        True if the token contains a blacklisted keyword.
    """
    return any(keyword in token for keyword in _BLACKLIST_KEYWORDS)
