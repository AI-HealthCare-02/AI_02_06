"""OCR service module — Producer 측 (FastAPI).

본 서비스는 HTTP 흐름의 thin layer 다:

- ``enqueue_ocr_task``: 업로드 bytes 를 RQ ``ai`` 큐에 enqueue, draft_id 즉시 반환
- ``get_draft_data``: Redis 폴링 — ``ocr_status`` / ``ocr_draft`` 키를 종합해 상태 반환
- ``confirm_and_save``: 사용자 검수가 끝난 약품 메타를 DB 에 영구 저장

OCR 자체 (CLOVA 호출 + 텍스트 정규화 + DB 매칭) 는 ai-worker 의
``ai_worker.domains.ocr.jobs.process_ocr_task`` 가 비동기로 처리한다.
LLM 은 더 이상 사용하지 않는다 — 약품 식별은 pg_trgm 매칭만으로 수행.
"""

from datetime import datetime
import os
from typing import Any
import uuid

from fastapi import UploadFile
from rq import Queue

from app.core.config import config
from app.core.redis_client import make_async_redis, make_sync_redis
from app.dtos.ocr import (
    ConfirmMedicationRequest,
    ExtractedMedicine,
    OcrDraftPollResponse,
    OcrDraftStatus,
    OcrExtractResponse,
)
from app.models.medication import Medication

_OCR_JOB_REF = "ai_worker.domains.ocr.jobs.process_ocr_task"
_DRAFT_TTL_SEC = 600  # 10분 — 사용자가 결과를 검수·확정하는 윈도우
_TERMINAL_STATUSES: dict[str, OcrDraftStatus] = {
    "no_text": OcrDraftStatus.NO_TEXT,
    "no_candidates": OcrDraftStatus.NO_CANDIDATES,
    "failed": OcrDraftStatus.FAILED,
}


class OCRService:
    """FastAPI 측 OCR thin service — RQ producer + 결과 폴링 + DB 저장."""

    def __init__(self) -> None:
        # 폴링·삭제용 async client + RQ enqueue 용 sync client. keepalive 일괄 적용.
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        self.redis = make_async_redis(redis_url, decode_responses=True)
        self._queue = Queue("ai", connection=make_sync_redis(redis_url))

    async def enqueue_ocr_task(self, file: UploadFile) -> OcrExtractResponse:
        """업로드 이미지를 ai-worker 로 enqueue 하고 draft_id 를 즉시 반환한다.

        Args:
            file: 사용자가 업로드한 처방전 이미지 (UploadFile).

        Returns:
            ``OcrExtractResponse`` — 빈 ``medicines`` 리스트와 ``draft_id`` 만 채워짐.
            프론트는 이 ID 로 폴링한다.
        """
        image_bytes = await file.read()
        draft_id = str(uuid.uuid4())
        filename = file.filename or "prescription.jpg"
        self._queue.enqueue(_OCR_JOB_REF, image_bytes, filename, draft_id)
        return OcrExtractResponse(draft_id=draft_id, medicines=[])

    async def get_draft_data(self, draft_id: str) -> OcrDraftPollResponse:
        """폴링 — ai-worker 의 처리 상태를 종합해 반환한다.

        우선순위:
        1. ``ocr_status:{draft_id}`` 가 있고 terminal (no_text/no_candidates/failed) → 해당 상태
        2. ``ocr_draft:{draft_id}`` 가 있으면 → READY + medicines
        3. 둘 다 없으면 → PENDING (아직 처리 중)

        Args:
            draft_id: enqueue 응답의 draft_id.

        Returns:
            ``OcrDraftPollResponse`` — 항상 status 를 동봉.
        """
        terminal = await self._read_terminal_status(draft_id)
        if terminal is not None:
            return OcrDraftPollResponse(draft_id=draft_id, status=terminal, medicines=[])

        draft_json = await self.redis.get(f"ocr_draft:{draft_id}")
        if draft_json:
            extracted = OcrExtractResponse.model_validate_json(draft_json)
            return OcrDraftPollResponse(
                draft_id=draft_id,
                status=OcrDraftStatus.READY,
                medicines=extracted.medicines,
            )
        return OcrDraftPollResponse(draft_id=draft_id, status=OcrDraftStatus.PENDING, medicines=[])

    async def _read_terminal_status(self, draft_id: str) -> OcrDraftStatus | None:
        """``ocr_status:{draft_id}`` 키에 terminal 상태가 있으면 반환."""
        status_value = await self.redis.get(f"ocr_status:{draft_id}")
        if status_value is None:
            return None
        return _TERMINAL_STATUSES.get(status_value)

    async def confirm_and_save(
        self,
        request: ConfirmMedicationRequest,
        profile_id: str,
    ) -> dict[str, Any]:
        """사용자 검수 완료된 약품 메타를 DB 에 영구 저장한다.

        Redis 의 draft 키는 atomic delete 로 게이트해 중복 저장을 방지한다.

        Args:
            request: 사용자가 검수·수정한 최종 약품 리스트.
            profile_id: 약품을 등록할 프로필 ID.

        Returns:
            ``{"status": "success", "message": str}``.

        Raises:
            ValueError: 이미 처리되었거나 만료된 draft.
        """
        deleted = await self.redis.delete(f"ocr_draft:{request.draft_id}")
        if deleted == 0:
            raise ValueError("이미 처리된 요청입니다. 새로 처방전을 등록해주세요.")
        await self.redis.delete(f"ocr_status:{request.draft_id}")

        saved = [await self._save_one_medication(med, profile_id) for med in request.confirmed_medicines]
        return {
            "status": "success",
            "message": f"{len(saved)}개의 약품이 성공적으로 저장되었습니다.",
        }

    async def _save_one_medication(self, med: ExtractedMedicine, profile_id: str) -> Medication:
        """확정된 약품 한 건을 ``Medication`` 으로 저장."""
        daily_count = med.daily_intake_count or 1
        total_days = med.total_intake_days or 1
        total_count = daily_count * total_days
        today = datetime.now(tz=config.TIMEZONE).date()
        return await Medication.create(
            profile_id=profile_id,
            medicine_name=med.medicine_name,
            department=med.department,
            category=med.category,
            dose_per_intake=med.dose_per_intake,
            intake_instruction=med.intake_instruction,
            daily_intake_count=daily_count,
            total_intake_days=total_days,
            intake_times=[],  # TODO: 복용 시간 설정 기능 (다음 sprint)
            total_intake_count=total_count,
            remaining_intake_count=total_count,
            start_date=med.dispensed_date or today,
            dispensed_date=med.dispensed_date,
            is_active=True,
        )
