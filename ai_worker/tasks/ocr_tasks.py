"""OCR task module for prescription image processing.

This module provides RQ tasks for the OCR pipeline:
1. OpenCV preprocessing -> CLOVA OCR -> text postprocessing
   -> medicine_info DB matching -> Redis result storage
2. Medication guide generation (separate task, uses LLM)

LLM is NOT used in OCR parsing. Medicine identification relies on
DB matching against the medicine_info table (public API data).
LLM is reserved for the RAG pipeline (Phase 3).
"""

import json
from pathlib import Path
import time
import uuid

import httpx
import redis

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger
from ai_worker.utils.image_preprocessor import preprocess_for_ocr
from ai_worker.utils.text_postprocessor import clean_ocr_text, extract_medicine_candidates
from app.dtos.ocr import ExtractedMedicine, OcrExtractResponse

logger = get_logger(__name__)


# ── CLOVA OCR API 호출 (httpx 동기 방식, RQ 워커에서 실행) ────────────


def _call_clova_ocr(image_path: str) -> str:
    """Call CLOVA OCR API with httpx (worker internal use).

    Args:
        image_path: Path to the image file for OCR processing.

    Returns:
        Extracted text string from the OCR response.

    Raises:
        ValueError: If CLOVA OCR config is missing.
        httpx.HTTPStatusError: If OCR API request fails.
    """
    invoke_url = config.CLOVA_OCR_URL
    secret_key = config.CLOVA_OCR_SECRET

    if not invoke_url or not secret_key:
        raise ValueError("OCR 처리 실패: CLOVA_OCR 설정이 누락되었습니다.")

    path = Path(image_path)
    ext = path.suffix.lstrip(".").lower()

    request_json = {
        "images": [{"format": ext, "name": path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": round(time.time() * 1000),
    }

    try:
        with path.open("rb") as f:
            response = httpx.post(
                invoke_url,
                headers={"X-OCR-SECRET": secret_key},
                data={"message": json.dumps(request_json).encode("UTF-8")},
                files=[("file", f)],
                timeout=30.0,
            )
        response.raise_for_status()
        fields = response.json()["images"][0]["fields"]
        return " ".join(field["inferText"] for field in fields)
    except httpx.HTTPStatusError:
        logger.exception("CLOVA OCR API error for %s", image_path)
        raise
    except Exception:
        logger.exception("CLOVA OCR unexpected error for %s", image_path)
        raise


# ── medicine_info DB 매칭 (유사도 검색 -> 정확 매칭 2단계) ────────────
# Step 3.5: pg_trgm 유사도 검색 (OCR 오타 보정, 예: "다이레놀" -> "타이레놀")
# Step 4:   매칭 결과 확정 -> ExtractedMedicine 리스트 반환
# LLM은 사용하지 않음. 문자 수준 유사도로 약품 식별


def _match_candidates_from_db(candidates: list[str]) -> list[ExtractedMedicine]:
    """Match medicine name candidates against medicine_info DB.

    Uses a 2-step matching strategy:
    1. Exact/partial match (ILIKE) - fast, handles clean OCR text
    2. Trigram fuzzy search (pg_trgm) - handles OCR typos

    Args:
        candidates: List of medicine name candidate strings
            from OCR text postprocessing.

    Returns:
        List of ExtractedMedicine with matched medicine names.
    """
    import asyncio

    from app.repositories.medicine_info_repository import MedicineInfoRepository

    repo = MedicineInfoRepository()
    matched: list[ExtractedMedicine] = []
    seen_names: set[str] = set()

    async def _search() -> None:
        # pg_trgm 확장 활성화 (최초 1회만 실제 실행됨)
        await repo.ensure_pg_trgm()

        for candidate in candidates:
            # Step 1: 정확/부분 일치 시도 (빠름)
            results = await repo.search_by_name(candidate, limit=1)

            # Step 2: 매칭 실패 시 유사도 검색 (OCR 오타 보정)
            if not results:
                fuzzy_results = await repo.fuzzy_search_by_name(
                    candidate,
                    threshold=0.3,
                    limit=1,
                )
                if fuzzy_results:
                    best = fuzzy_results[0]
                    logger.info(
                        "Fuzzy matched: '%s' -> '%s' (score: %.2f)",
                        candidate,
                        best["medicine_name"],
                        best["score"],
                    )
                    medicine = await repo.get_by_id(best["id"])
                    if medicine and medicine.medicine_name not in seen_names:
                        seen_names.add(medicine.medicine_name)
                        matched.append(
                            ExtractedMedicine(
                                medicine_name=medicine.medicine_name,
                                category=medicine.category,
                            )
                        )
                continue

            medicine = results[0]
            if medicine.medicine_name in seen_names:
                continue

            seen_names.add(medicine.medicine_name)
            matched.append(
                ExtractedMedicine(
                    medicine_name=medicine.medicine_name,
                    category=medicine.category,
                )
            )

    # RQ 워커는 동기 환경이므로 asyncio.run으로 실행
    asyncio.run(_search())

    logger.info(
        "DB matching: %d candidates -> %d matched medicines",
        len(candidates),
        len(matched),
    )
    return matched


# ── OCR 전체 파이프라인 (RQ Task) ────────────────────────────────────
# 흐름: OpenCV 전처리 -> CLOVA OCR -> 텍스트 후처리
#       -> pg_trgm 유사도 검색 (오타 보정) -> DB 매칭 확정
#       -> Redis에 결과 저장 (10분 만료)
# 참고: LLM은 사용하지 않음. Phase 3 RAG에서만 LLM 사용


def process_ocr_task(image_path: str, draft_id: str) -> bool:
    """[RQ Task] OCR extraction and DB matching pipeline.

    Processes prescription image through OpenCV preprocessing,
    CLOVA OCR text extraction, text postprocessing, and
    medicine_info DB matching. Results stored in Redis.

    Args:
        image_path: Path to the uploaded prescription image.
        draft_id: Unique ID for Redis temporary storage.

    Returns:
        True if processing succeeded, False otherwise.
    """
    logger.info("Starting OCR task: %s (Draft ID: %s)", image_path, draft_id)

    # Redis 연결 (동기 방식)
    redis_conn = redis.from_url(config.REDIS_URL, decode_responses=True)

    try:
        # Step 1: OpenCV 전처리 (그레이스케일 -> 블러 -> 이진화 -> 모폴로지)
        preprocessed_path = preprocess_for_ocr(image_path)
        logger.info("Image preprocessed: %s", preprocessed_path)

        # Step 2: CLOVA OCR 호출 -> Raw 텍스트 추출
        raw_text = _call_clova_ocr(preprocessed_path)
        if not raw_text.strip():
            logger.warning("No text extracted from image: %s", image_path)
            redis_conn.setex(f"ocr_status:{draft_id}", 600, "no_text")
            return False

        # Step 3: 텍스트 후처리 (복용지시/날짜/블랙리스트 제거 -> 약품명 후보 추출)
        cleaned_text = clean_ocr_text(raw_text)
        candidates = extract_medicine_candidates(cleaned_text)

        if not candidates:
            logger.warning("No medicine candidates found in OCR text")
            redis_conn.setex(f"ocr_status:{draft_id}", 600, "no_candidates")
            return False

        # Step 4: medicine_info DB 매칭 (LLM 없이 DB 검색으로 약품 확정)
        matched_medicines = _match_candidates_from_db(candidates)

        # Step 5: 결과를 Redis에 저장 (10분 만료, 프론트에서 폴링)
        response_obj = OcrExtractResponse(draft_id=draft_id, medicines=matched_medicines)
        redis_conn.setex(f"ocr_draft:{draft_id}", 600, response_obj.model_dump_json())

        logger.info(
            "OCR task complete for %s: %d candidates -> %d matched",
            draft_id,
            len(candidates),
            len(matched_medicines),
        )
        return True

    except Exception:
        logger.exception("OCR task failed for %s", draft_id)
        redis_conn.setex(f"ocr_status:{draft_id}", 600, "failed")
        return False
    finally:
        # 임시 이미지 파일 정리
        Path(image_path).unlink(missing_ok=True)
        preprocessed = Path(image_path).parent / f"{Path(image_path).stem}_preprocessed{Path(image_path).suffix}"
        preprocessed.unlink(missing_ok=True)
