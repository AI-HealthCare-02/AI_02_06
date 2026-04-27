"""Reusable keyword-based filters for public-API drug data.

Centralizes the keyword sets and predicates used across services that
ingest data from the Food and Drug Safety public API. Both the
medicine_info sync (`medicine_data_service`) and the upcoming drug
recall sync (`drug_recall_service`) feed raw `ITEM_NAME` / `prdtName`
strings through these helpers, so they live here as pure functions to
avoid drift between two copies of the same regex.

Categories:
    Hospital-only injectables / infusions / implants — excluded from
    the consumer DB, but self-injectable drugs (insulin, saxenda, etc.)
    are kept.

Note:
    Pure functions only. No I/O, no DB, no logging. Safe to import
    from any layer (services, scripts, tests).
"""

# ── 병원 전용 의약품 키워드 (주사·수액·이식 + 병원 인프라용 제형) ────
# 흐름: 키워드 매칭 → 자가주사 화이트리스트 검사 → 최종 판정
_HOSPITAL_ONLY_KEYWORDS: tuple[str, ...] = (
    "주사",
    "수액",
    "이식",
)

# ── 자가주사 가능 약제 화이트리스트 (병원 전용에서 예외 처리) ──────────
_SELF_INJECT_KEYWORDS: tuple[str, ...] = (
    "인슐린",
    "삭센다",
    "자가주사",
    "펜주",
    "프리필드",
)


def is_hospital_only(product_name: str) -> bool:
    """Check whether a product name indicates a hospital-only formulation.

    A product is considered hospital-only when it matches any of the
    exclusion keywords (injection, infusion, implant) AND does not
    match any self-inject whitelist keyword (insulin, saxenda, etc.).

    Args:
        product_name: Korean product name as returned by the public API
            (`ITEM_NAME` for permits, `prdtName` for recalls).

    Returns:
        True if the product should be excluded from the consumer DB,
        False otherwise. Empty / non-string input returns False so the
        caller can decide separately how to handle missing names.
    """
    if not product_name:
        return False

    has_exclude = any(kw in product_name for kw in _HOSPITAL_ONLY_KEYWORDS)
    if not has_exclude:
        return False

    has_self_inject = any(kw in product_name for kw in _SELF_INJECT_KEYWORDS)
    return not has_self_inject
