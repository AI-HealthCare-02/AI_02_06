"""OCR 후보 토큰을 medicine_info DB 와 매칭한다. (아키텍트 패러다임 시프트 버전)"""

import asyncio
import json
import logging

from tortoise import Tortoise

from ai_worker.core.openai_client import get_openai_client
from app.db.databases import TORTOISE_ORM
from app.dtos.ocr import ExtractedMedicine
from app.repositories.medicine_info_repository import MedicineInfoRepository

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 0.3
_FUZZY_LIMIT = 1


async def search_candidates_in_open_db(candidates: list[str]) -> list[ExtractedMedicine]:
    if not candidates:
        return []

    full_text = " ".join(candidates)
    logger.info("Reconstructed OCR Text Length: %d", len(full_text))

    # 💡 LLM이 이름, 용량, 타입을 분리해서 가져옵니다.
    extracted_items = await _extract_medicines_with_llm(full_text)
    logger.info("LLM Extracted Items: %s", extracted_items)

    matched: list[ExtractedMedicine] = []
    seen_names: set[str] = set()
    repo = MedicineInfoRepository()
    await repo.ensure_pg_trgm()

    db_match_count = 0
    for item in extracted_items:
        pure_name = item.get("name", "")
        strength = item.get("strength", "")  # 💡 잃어버린 용량 구출!
        item_type = item.get("type", "의약품")

        if not pure_name:
            continue

        if await _match_clean_name(repo, pure_name, strength, item_type, matched, seen_names):
            db_match_count += 1
        elif pure_name not in seen_names:
            seen_names.add(pure_name)

            # 💡 동훈 님 요청사항: 문구 변경 및 용량 부착
            final_display_name = f"{pure_name} {strength}".strip()
            if item_type == "영양제":
                display_category = "영양제/보충제"
                final_display_name += " (영양제 성분 포함)"
            else:
                display_category = "미분류(수동확인)"

            matched.append(
                ExtractedMedicine(
                    medicine_name=final_display_name,
                    category=display_category,
                    raw_ocr_name=pure_name,
                    is_llm_corrected=True,
                    match_score=0.5,
                )
            )

    logger.info("Final Matching: %d LLM names -> %d matched to DB", len(extracted_items), db_match_count)
    return matched


def match_candidates_to_medicines(candidates: list[str]) -> list[ExtractedMedicine]:
    return asyncio.run(_run_with_db_lifecycle(candidates))


async def _run_with_db_lifecycle(candidates: list[str]) -> list[ExtractedMedicine]:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        return await search_candidates_in_open_db(candidates)
    finally:
        await Tortoise.close_connections()


# 💡 strength(용량)과 item_type을 파라미터로 추가로 받습니다.
async def _match_clean_name(
    repo: MedicineInfoRepository,
    pure_name: str,
    strength: str,
    item_type: str,
    matched: list[ExtractedMedicine],
    seen_names: set[str],
) -> bool:

    # 조립된 최종 화면 표시용 이름 (이름 + 용량 + 영양제 꼬리표)
    def _build_display_name(base_name: str) -> str:
        name_with_strength = f"{base_name} {strength}".strip()
        if item_type == "영양제":
            return f"{name_with_strength} (영양제 성분 포함)"
        return name_with_strength

    exact_results = await repo.search_by_name(pure_name, limit=1)
    if exact_results:
        med = exact_results[0]
        if pure_name not in seen_names:
            seen_names.add(pure_name)
            matched.append(
                ExtractedMedicine(
                    medicine_name=_build_display_name(med.medicine_name),  # 💡 DB 이름 뒤에 용량을 예쁘게 조립!
                    category=med.category,
                    raw_ocr_name=pure_name,
                    is_llm_corrected=True,
                    match_score=1.0,
                )
            )
        return True

    fuzzy_results = await repo.fuzzy_search_by_name(pure_name, threshold=_FUZZY_THRESHOLD, limit=_FUZZY_LIMIT)
    if fuzzy_results:
        best = fuzzy_results[0]
        med = await repo.get_by_id(best["id"])
        if med and pure_name not in seen_names:
            seen_names.add(pure_name)
            matched.append(
                ExtractedMedicine(
                    medicine_name=_build_display_name(med.medicine_name),  # 💡 DB 이름 뒤에 용량을 예쁘게 조립!
                    category=med.category,
                    raw_ocr_name=pure_name,
                    is_llm_corrected=True,
                    match_score=best["score"],
                )
            )
        return True

    return False


async def _extract_medicines_with_llm(raw_text: str) -> list[dict]:
    """LLM을 호출하여 이름, 용량, 유형을 정밀하게 분리 추출한다."""
    client = get_openai_client()
    if not client:
        logger.error("OPENAI_API_KEY 미설정. LLM 동작 불가.")
        return []

    # 프롬프트 재진화: 이름과 용량을 강제로 분리시킨다.
    prompt = f"""
    너는 대한민국 최고 수준의 약사 AI야.
    다음은 처방전 사진을 OCR로 읽어낸 텍스트야.

    [OCR 전체 문맥 텍스트]
    "{raw_text}"

    [지시사항]
    1. 환자명(홍길동 등), 병원명(SEOUL 등), 주소, 성별, 나이 등 노이즈는 완전히 무시해.
    2. 텍스트 중에서 '의약품'과 '영양제/보충제(마그네슘 등)'를 추출해.
    3. 텍스트에 용량(예: 500mg, 100밀리그램, 0.5g 등)이 있다면, 반드시
       약품명과 분리해서 추출해.
       예: 타이레놀정500mg -> 이름: 타이레놀정, 용량: 500mg
    4. 응답은 각 항목의 순수 이름(name), 용량(strength), 유형(type:
       "의약품" 또는 "영양제")을 포함한 JSON 객체 배열 형태로 반환해.

    [출력 예시]
    {{
        "items": [
            {{"name": "타이레놀정", "strength": "500mg", "type": "의약품"}},
            {{"name": "아스피린장용정", "strength": "100mg", "type": "의약품"}},
            {{"name": "마그네슘", "strength": "", "type": "영양제"}}
        ]
    }}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("items", [])
    except Exception as e:
        logger.error(f"LLM 텍스트 추출 실패: {e}")
        return []
