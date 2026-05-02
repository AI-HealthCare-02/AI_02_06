"""OCR 후보 토큰을 medicine_info DB 와 매칭한다. (아키텍트 패러다임 시프트 버전)

기존의 단어별 쪼개기 매칭을 버리고, 전체 텍스트를 LLM에게 넘겨 문맥을 통해
노이즈(홍길동, 병원명)를 제거하고 진짜 약품명만 교정하여 추출하는 혁신 파이프라인.
"""

import asyncio
import logging
import json

from tortoise import Tortoise

from app.db.databases import TORTOISE_ORM
from app.dtos.ocr import ExtractedMedicine
from app.repositories.medicine_info_repository import MedicineInfoRepository
from ai_worker.core.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# LLM이 1차로 예쁘게 정제해 주므로, 퍼지 매칭은 0.3으로 넉넉하게 잡습니다.
_FUZZY_THRESHOLD = 0.3
_FUZZY_LIMIT = 1

async def search_candidates_in_open_db(candidates: list[str]) -> list[ExtractedMedicine]:
    if not candidates:
        return []

    # 1. 87개로 산산조각 난 토큰을 다시 하나의 긴 문장으로 이어 붙인다 (문맥 복원!)
    full_text = " ".join(candidates)
    logger.info("Reconstructed OCR Text Length: %d", len(full_text))

    # 2. LLM에게 노이즈 필터링 및 약품명 교정을 통째로 맡긴다
    clean_names = await _extract_medicines_with_llm(full_text)
    logger.info("LLM Extracted Clean Names: %s", clean_names)

    matched: list[ExtractedMedicine] = []
    seen_names: set[str] = set()
    repo = MedicineInfoRepository()
    await repo.ensure_pg_trgm()

    db_match_count = 0
    for name in clean_names:
        if await _match_clean_name(repo, name, matched, seen_names):
            db_match_count += 1
        else:
            # DB 매칭에 실패해도 LLM이 뽑은 이름은 신뢰성이 높으므로 Fallback으로 추가
            if name not in seen_names:
                seen_names.add(name)
                matched.append(ExtractedMedicine(
                    medicine_name=name,
                    raw_ocr_name=name,
                    is_llm_corrected=True,
                    match_score=0.5
                ))

    logger.info("Final Matching: %d LLM names -> %d matched to DB", len(clean_names), db_match_count)
    return matched

def match_candidates_to_medicines(candidates: list[str]) -> list[ExtractedMedicine]:
    return asyncio.run(_run_with_db_lifecycle(candidates))

async def _run_with_db_lifecycle(candidates: list[str]) -> list[ExtractedMedicine]:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        return await search_candidates_in_open_db(candidates)
    finally:
        await Tortoise.close_connections()

async def _match_clean_name(repo: MedicineInfoRepository, name: str, matched: list[ExtractedMedicine], seen_names: set[str]) -> bool:
    # 1. 정확 일치 검사
    exact_results = await repo.search_by_name(name, limit=1)
    if exact_results:
        med = exact_results[0]
        if med.medicine_name not in seen_names:
            seen_names.add(med.medicine_name)
            matched.append(ExtractedMedicine(
                medicine_name=med.medicine_name,
                category=med.category,
                raw_ocr_name=name,
                is_llm_corrected=True,
                match_score=1.0
            ))
        return True

    # 2. 퍼지 매칭 검사 (LLM이 교정했지만 띄어쓰기 등이 다를 수 있음)
    fuzzy_results = await repo.fuzzy_search_by_name(name, threshold=_FUZZY_THRESHOLD, limit=_FUZZY_LIMIT)
    if fuzzy_results:
        best = fuzzy_results[0]
        med = await repo.get_by_id(best["id"])
        if med and med.medicine_name not in seen_names:
            seen_names.add(med.medicine_name)
            matched.append(ExtractedMedicine(
                medicine_name=med.medicine_name,
                category=med.category,
                raw_ocr_name=name,
                is_llm_corrected=True,
                match_score=best["score"]
            ))
        return True

    return False

async def _extract_medicines_with_llm(raw_text: str) -> list[str]:
    """LLM을 호출하여 노이즈를 날리고 약품명만 JSON 배열로 추출한다."""
    client = get_openai_client()
    if not client:
        logger.error("OPENAI_API_KEY 미설정. LLM 동작 불가.")
        return []

    prompt = f"""
    너는 대한민국 최고 수준의 약사 AI야.
    다음은 처방전 사진을 OCR로 읽어낸 텍스트야. 의미 없는 단어(병원명, 환자명, 주소, 무작위 글자)와 약품명이 뒤섞여 있어.
    
    [OCR 전체 문맥 텍스트]
    "{raw_text}"
    
    [지시사항]
    1. 환자명(홍길동 등), 병원명(SEOUL 등), 주소, 성별, 나이 등 약품과 관련 없는 '노이즈'는 완전히 무시해! 절대 결과에 포함하지 마.
    2. 텍스트 중에서 1일 N회, 식후 등 용법과 같이 적혀있는 실제 '약품'만 추출해.
    3. '다이레놀', '우류사' 처럼 명백한 오타가 있다면 올바른 정식 약품명(타이레놀정500밀리그램, 우루사정100밀리그램 등)으로 반드시 교정해.
    4. 응답은 오직 교정된 약품명 문자열들만 포함된 JSON 배열 형태로 반환해.
    
    [출력 예시]
    {{
        "medicines": ["타이레놀정500밀리그램", "아스피린장용정100밀리그램", "우루사정100밀리그램"]
    }}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0.0
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("medicines", [])
    except Exception as e:
        logger.error(f"LLM 텍스트 추출 실패: {e}")
        return []