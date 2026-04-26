"""OCR 후보 토큰을 medicine_info DB 와 매칭한다.

3단계 매칭 전략:
1. **정확/부분 일치 (ILIKE)** — 빠르고 깨끗한 OCR 텍스트에 효과적
2. **트라이그램 유사도 (pg_trgm)** — OCR 오타 보정 ("다이레놀" → "타이레놀")
3. **Fallback (raw 후보)** — DB 매칭 실패 시 약품명 패턴 휴리스틱 통과한
   원본 토큰을 그대로 ``ExtractedMedicine`` 으로 추가. 사용자가 검수 화면에서
   직접 수정·삭제할 수 있도록 정보를 잃지 않는 정책.

LLM 은 사용하지 않는다. 모든 매칭은 문자열 수준에서 끝난다.

ai-worker 프로세스는 부팅 시 Tortoise ORM 을 init 하지 않으므로 (FastAPI
lifespan 과 별개), 매 RQ job 마다 본 모듈이 직접 init -> 검색 -> close 로
짧게 connection lifecycle 을 관리한다.
"""

import asyncio
import logging

from tortoise import Tortoise

from app.db.databases import TORTOISE_ORM
from app.dtos.ocr import ExtractedMedicine
from app.models.medicine_info import MedicineInfo
from app.repositories.medicine_info_repository import MedicineInfoRepository

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 0.3
_FUZZY_LIMIT = 1
_EXACT_LIMIT = 1

# 약품명 패턴 종결어 — 한국 의약품 명명 관례.
# Fallback 단계에서 raw OCR 토큰을 추가할지 결정하는 휴리스틱 기준.
_MEDICINE_NAME_SUFFIXES: tuple[str, ...] = (
    "정",
    "캡슐",
    "캅셀",
    "시럽",
    "액",
    "주",
    "환",
    "산",
    "연고",
    "겔",
    "크림",
    "패치",
    "분말",
    "좌제",
    "주사",
    "주입",
)
_FALLBACK_MIN_LENGTH = 3


async def search_candidates_in_open_db(candidates: list[str]) -> list[ExtractedMedicine]:
    """후보 토큰 리스트를 약품 매칭한다 — Tortoise 가 이미 init 된 상태 가정.

    호출자가 lifecycle 을 관리하므로 (예: jobs.py 의 ``_async_db_part``) 본 함수는
    init/close 를 하지 않는다. ai-worker 안의 RQ task 가 1회 init 으로 매칭 +
    ``ocr_drafts`` UPDATE 를 모두 묶어 처리하기 위함.

    DB 매칭 실패한 후보 중 약품명 패턴 (정/캡슐/시럽/...) 을 가진 토큰은 raw
    상태로 추가한다.

    Args:
        candidates: ``extract_medicine_candidates`` 가 반환한 토큰 리스트.

    Returns:
        중복 제거된 ``ExtractedMedicine`` 리스트 (DB 매칭 우선, fallback 후순).
    """
    matched: list[ExtractedMedicine] = []
    db_match_count = await _search_into(candidates, matched)
    fallback_count = len(matched) - db_match_count
    logger.info(
        "DB matching: %d candidates -> %d matched (db=%d, fallback=%d)",
        len(candidates),
        len(matched),
        db_match_count,
        fallback_count,
    )
    return matched


def match_candidates_to_medicines(candidates: list[str]) -> list[ExtractedMedicine]:
    """후보 토큰 리스트를 약품 객체로 매핑한다 — 자체 Tortoise lifecycle 포함.

    스크립트·테스트 등 Tortoise 가 init 되지 않은 환경에서도 안전하게 호출할
    수 있도록 init/close 를 직접 관리한다. RQ task 안에서는 lifecycle 중복을
    피하기 위해 ``search_candidates_in_open_db`` 를 직접 호출하는 게 권장된다.

    Args:
        candidates: ``extract_medicine_candidates`` 가 반환한 토큰 리스트.

    Returns:
        중복 제거된 ``ExtractedMedicine`` 리스트.
    """
    return asyncio.run(_run_with_db_lifecycle(candidates))


async def _run_with_db_lifecycle(candidates: list[str]) -> list[ExtractedMedicine]:
    """Tortoise init -> 검색 -> close 를 묶어 한 번의 lifecycle 로 실행."""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        return await search_candidates_in_open_db(candidates)
    finally:
        await Tortoise.close_connections()


async def _search_into(candidates: list[str], matched: list[ExtractedMedicine]) -> int:
    """비동기 검색을 수행해 ``matched`` 리스트를 채운다 (in-place).

    DB 매칭 실패한 후보는 _add_fallback_if_likely 로 raw 추가 시도.

    Returns:
        DB 매칭에 성공한 후보 개수.
    """
    repo = MedicineInfoRepository()
    await repo.ensure_pg_trgm()
    seen_names: set[str] = set()
    db_match_count = 0
    unmatched: list[str] = []
    for candidate in candidates:
        if await _match_one(repo, candidate, matched, seen_names):
            db_match_count += 1
        else:
            unmatched.append(candidate)
    _append_raw_fallbacks(unmatched, matched, seen_names)
    return db_match_count


async def _match_one(
    repo: MedicineInfoRepository,
    candidate: str,
    matched: list[ExtractedMedicine],
    seen_names: set[str],
) -> bool:
    """단일 후보에 대해 정확 매칭 → 실패 시 fuzzy 매칭. 매칭 성공 시 True."""
    exact_results = await repo.search_by_name(candidate, limit=_EXACT_LIMIT)
    if exact_results:
        _append_unique(exact_results[0], matched, seen_names)
        return True

    fuzzy_match = await _try_fuzzy(repo, candidate)
    if fuzzy_match is not None:
        _append_unique(fuzzy_match, matched, seen_names)
        return True
    return False


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


def _append_raw_fallbacks(
    unmatched: list[str],
    matched: list[ExtractedMedicine],
    seen_names: set[str],
) -> None:
    """DB 매칭 실패 토큰 중 약품명 패턴을 통과한 것을 raw 로 추가한다.

    사용자가 검수 화면에서 직접 수정·삭제할 수 있도록 OCR 결과를 잃지 않는
    정책. 약품명 종결어 (정/캡슐/시럽/...) 와 최소 길이 휴리스틱으로 노이즈
    토큰 (병원명·환자명·날짜 잔재) 을 1차 차단한다.
    """
    for token in unmatched:
        if not _looks_like_medicine_name(token):
            continue
        if token in seen_names:
            continue
        seen_names.add(token)
        matched.append(ExtractedMedicine(medicine_name=token))


def _looks_like_medicine_name(token: str) -> bool:
    """약품명 패턴 휴리스틱 — 종결어 + 최소 길이."""
    if len(token) < _FALLBACK_MIN_LENGTH:
        return False
    return token.endswith(_MEDICINE_NAME_SUFFIXES)
