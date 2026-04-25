"""OCR 후보 토큰을 medicine_info DB 와 매칭한다.

2단계 매칭 전략:
1. **정확/부분 일치 (ILIKE)** — 빠르고 깨끗한 OCR 텍스트에 효과적
2. **트라이그램 유사도 (pg_trgm)** — OCR 오타 보정 ("다이레놀" → "타이레놀")

LLM 은 사용하지 않는다. 모든 매칭은 문자열 수준에서 끝난다.
"""

import asyncio
import logging

from app.dtos.ocr import ExtractedMedicine
from app.models.medicine_info import MedicineInfo
from app.repositories.medicine_info_repository import MedicineInfoRepository

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 0.3
_FUZZY_LIMIT = 1
_EXACT_LIMIT = 1


def match_candidates_to_medicines(candidates: list[str]) -> list[ExtractedMedicine]:
    """후보 토큰 리스트를 medicine_info 의 약품 객체 리스트로 매핑한다.

    동기 RQ task 내부에서 호출되므로 ``asyncio.run`` 으로 비동기 검색을
    감싸 실행한다.

    Args:
        candidates: ``extract_medicine_candidates`` 가 반환한 토큰 리스트.

    Returns:
        중복 제거된 ``ExtractedMedicine`` 리스트 (입력 순서 유지).
    """
    matched: list[ExtractedMedicine] = []
    asyncio.run(_search_into(candidates, matched))
    logger.info(
        "DB matching: %d candidates -> %d matched medicines",
        len(candidates),
        len(matched),
    )
    return matched


async def _search_into(candidates: list[str], matched: list[ExtractedMedicine]) -> None:
    """비동기 검색을 수행해 ``matched`` 리스트를 채운다 (in-place)."""
    repo = MedicineInfoRepository()
    await repo.ensure_pg_trgm()
    seen_names: set[str] = set()
    for candidate in candidates:
        await _match_one(repo, candidate, matched, seen_names)


async def _match_one(
    repo: MedicineInfoRepository,
    candidate: str,
    matched: list[ExtractedMedicine],
    seen_names: set[str],
) -> None:
    """단일 후보에 대해 정확 매칭 → 실패 시 fuzzy 매칭 흐름을 실행한다."""
    exact_results = await repo.search_by_name(candidate, limit=_EXACT_LIMIT)
    if exact_results:
        _append_unique(exact_results[0], matched, seen_names)
        return

    fuzzy_match = await _try_fuzzy(repo, candidate)
    if fuzzy_match is not None:
        _append_unique(fuzzy_match, matched, seen_names)


async def _try_fuzzy(repo: MedicineInfoRepository, candidate: str) -> MedicineInfo | None:
    """pg_trgm 유사도 검색 — score 가 임계치 이상인 1건을 반환."""
    fuzzy_results = await repo.fuzzy_search_by_name(
        candidate,
        threshold=_FUZZY_THRESHOLD,
        limit=_FUZZY_LIMIT,
    )
    if not fuzzy_results:
        return None
    best = fuzzy_results[0]
    logger.info(
        "Fuzzy matched: '%s' -> '%s' (score: %.2f)",
        candidate,
        best["medicine_name"],
        best["score"],
    )
    return await repo.get_by_id(best["id"])


def _append_unique(
    medicine: MedicineInfo | None,
    matched: list[ExtractedMedicine],
    seen_names: set[str],
) -> None:
    """이미 본 약품이면 skip, 새로 발견하면 ``matched`` 에 추가."""
    if medicine is None or medicine.medicine_name in seen_names:
        return
    seen_names.add(medicine.medicine_name)
    matched.append(
        ExtractedMedicine(
            medicine_name=medicine.medicine_name,
            category=medicine.category,
        )
    )
