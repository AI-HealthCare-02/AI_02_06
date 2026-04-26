"""OCR RQ jobs — FastAPI 가 ``ai`` 큐로 enqueue 하는 진입점.

본 모듈은 RQ task entry point 만 정의한다. 실제 비즈니스 로직은
도메인 안의 다른 모듈로 위임한다:

- CLOVA OCR 호출 → ``text_extractor``
- 텍스트 정규화 → ``text_normalizer``
- DB 매칭 → ``medicine_matcher``
- Redis 결과 publish → ``ai_worker.core.rq_result_publisher``

흐름: CLOVA OCR -> 텍스트 정규화 -> 후보 추출 -> DB 매칭
       -> Redis SETEX (10분 TTL)

이미지는 디스크에 저장하지 않고 RQ payload 의 bytes 로 직접 받는다 —
공유 볼륨이 필요 없고, RQ job 종료 시 Redis 가 자동으로 args 를 정리한다.
"""

import redis

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger
from ai_worker.core.redis_client import make_sync_redis
from ai_worker.core.rq_result_publisher import publish_result
from ai_worker.domains.ocr.medicine_matcher import match_candidates_to_medicines
from ai_worker.domains.ocr.text_extractor import extract_text_from_image_bytes
from ai_worker.domains.ocr.text_normalizer import clean_ocr_text, extract_medicine_candidates
from app.dtos.ocr import OcrExtractResponse

logger = get_logger(__name__)

_RESULT_TTL_SEC = 600  # 10분 — 프론트가 폴링으로 회수하는 동안 보관


def process_ocr_task(image_bytes: bytes, filename: str, draft_id: str) -> bool:
    """[RQ Task] 처방전 이미지 한 장을 처리해 약품 인식 결과를 Redis 에 저장한다.

    Args:
        image_bytes: 업로드된 처방전 이미지의 raw bytes (FastAPI 가 read 한 결과).
        filename: 원본 파일명 — CLOVA OCR payload 에 전달.
        draft_id: Redis 임시 저장에 쓰일 고유 ID.

    Returns:
        성공 시 ``True``, 실패 시 ``False``.
    """
    logger.info("Starting OCR task: filename=%s draft_id=%s size=%d", filename, draft_id, len(image_bytes))
    redis_conn = make_sync_redis(config.REDIS_URL, decode_responses=True)

    try:
        return _run_pipeline(redis_conn, image_bytes, filename, draft_id)
    except Exception:
        logger.exception("OCR task failed for %s", draft_id)
        publish_result(redis_conn, f"ocr_status:{draft_id}", "failed", _RESULT_TTL_SEC)
        return False


def _run_pipeline(redis_conn: redis.Redis, image_bytes: bytes, filename: str, draft_id: str) -> bool:
    """이미지 bytes 를 받아 OCR -> 매칭 -> publish 까지 실행한다."""
    raw_text = extract_text_from_image_bytes(image_bytes, filename)
    if not raw_text.strip():
        logger.warning("No text extracted from image: %s", filename)
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
