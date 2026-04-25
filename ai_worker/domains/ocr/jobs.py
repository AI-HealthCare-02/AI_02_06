"""OCR RQ jobs — FastAPI 가 ``ai`` 큐로 enqueue 하는 진입점.

본 모듈은 RQ task entry point 만 정의한다. 실제 비즈니스 로직은
도메인 안의 다른 모듈로 위임한다:

- 이미지 전처리 → ``image_preprocessor``
- CLOVA OCR 호출 → ``text_extractor``
- 텍스트 정규화 → ``text_normalizer``
- DB 매칭 → ``medicine_matcher``
- Redis 결과 publish → ``ai_worker.core.rq_result_publisher``

흐름: 전처리 → CLOVA OCR → 텍스트 정규화 → 후보 추출 → DB 매칭
       → Redis SETEX (10분 TTL)
"""

import redis

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger
from ai_worker.core.redis_client import make_sync_redis
from ai_worker.core.rq_result_publisher import publish_result
from ai_worker.domains.ocr.image_preprocessor import preprocess_for_ocr
from ai_worker.domains.ocr.medicine_matcher import match_candidates_to_medicines
from ai_worker.domains.ocr.text_extractor import extract_text_from_image
from ai_worker.domains.ocr.text_normalizer import clean_ocr_text, extract_medicine_candidates
from app.dtos.ocr import OcrExtractResponse

logger = get_logger(__name__)

_RESULT_TTL_SEC = 600  # 10분 — 프론트가 폴링으로 회수하는 동안 보관


def process_ocr_task(image_path: str, draft_id: str) -> bool:
    """[RQ Task] 처방전 이미지 한 장을 처리해 약품 인식 결과를 Redis 에 저장한다.

    Args:
        image_path: 업로드된 처방전 이미지의 절대 경로.
        draft_id: Redis 임시 저장에 쓰일 고유 ID.

    Returns:
        성공 시 ``True``, 실패 시 ``False``.
    """
    logger.info("Starting OCR task: %s (Draft ID: %s)", image_path, draft_id)
    redis_conn = make_sync_redis(config.REDIS_URL, decode_responses=True)
    preprocessed_path: str | None = None

    try:
        preprocessed_path = preprocess_for_ocr(image_path)
        logger.info("Image preprocessed: %s", preprocessed_path)
        return _run_pipeline(redis_conn, preprocessed_path, draft_id)
    except Exception:
        logger.exception("OCR task failed for %s", draft_id)
        publish_result(redis_conn, f"ocr_status:{draft_id}", "failed", _RESULT_TTL_SEC)
        return False
    finally:
        _cleanup(image_path, preprocessed_path)


def _run_pipeline(redis_conn: redis.Redis, preprocessed_path: str, draft_id: str) -> bool:
    """전처리된 이미지를 받아 OCR → 매칭 → publish 까지 실행한다."""
    raw_text = extract_text_from_image(preprocessed_path)
    if not raw_text.strip():
        logger.warning("No text extracted from image: %s", preprocessed_path)
        publish_result(redis_conn, f"ocr_status:{draft_id}", "no_text", _RESULT_TTL_SEC)
        return False

    candidates = extract_medicine_candidates(clean_ocr_text(raw_text))
    if not candidates:
        logger.warning("No medicine candidates found in OCR text")
        publish_result(redis_conn, f"ocr_status:{draft_id}", "no_candidates", _RESULT_TTL_SEC)
        return False

    matched = match_candidates_to_medicines(candidates)
    response = OcrExtractResponse(draft_id=draft_id, medicines=matched)
    publish_result(redis_conn, f"ocr_draft:{draft_id}", response.model_dump_json(), _RESULT_TTL_SEC)
    logger.info(
        "OCR task complete for %s: %d candidates -> %d matched",
        draft_id,
        len(candidates),
        len(matched),
    )
    return True


def _cleanup(original_path: str, preprocessed_path: str | None) -> None:
    """원본/전처리 이미지 파일을 디스크에서 제거 (실패 무시)."""
    from pathlib import Path

    for p in (original_path, preprocessed_path):
        if not p:
            continue
        try:
            Path(p).unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to cleanup file: %s", p)
