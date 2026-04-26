"""OCR service — Producer 측 (FastAPI), DB 영속 저장 정책.

본 서비스는 HTTP 흐름의 thin layer 다:

- ``enqueue_ocr_task``: 업로드 bytes -> dedup 체크 -> ocr_drafts INSERT
  (또는 기존 활성 draft 재사용) -> RQ ``ai`` 큐에 enqueue -> draft_id 반환
- ``get_draft_data``: ocr_drafts SELECT -> ``OcrDraftPollResponse`` (단발 조회)
- ``stream_draft_states``: SSE 용 async generator — status 변화 시점마다 yield,
  terminal 도달 또는 max_seconds 초과 시 close
- ``list_active_drafts``: main 페이지 카드용 — 24h 안 미consume draft 리스트
- ``confirm_and_save``: ocr_drafts 의 consumed_at 을 atomic 으로 설정한 뒤
  Medication 영구 저장

OCR 자체 (CLOVA 호출 + 텍스트 정규화 + DB 매칭) 는 ai-worker 의
``ai_worker.domains.ocr.jobs.process_ocr_task`` 가 비동기로 처리하고
ocr_drafts 를 직접 UPDATE 한다. Redis 는 더 이상 결과 저장에 사용하지 않으며
RQ 큐 broker 로만 쓰인다.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
import hashlib
import json
import os
import time
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from rq import Queue

from app.core.config import config
from app.core.redis_client import make_sync_redis
from app.dtos.ocr import (
    ConfirmMedicationRequest,
    ExtractedMedicine,
    OcrActiveDraftsResponse,
    OcrDraftPollResponse,
    OcrDraftStatus,
    OcrDraftSummary,
    OcrExtractResponse,
)
from app.models.medication import Medication
from app.models.ocr_draft import OcrDraft
from app.repositories.ocr_draft_repository import OcrDraftRepository

_OCR_JOB_REF = "ai_worker.domains.ocr.jobs.process_ocr_task"

# SSE long-polling 정책 — nginx default proxy_read_timeout(60s) 안에 close
_STREAM_MAX_SECONDS = 50
_STREAM_TICK_SECONDS = 0.5


class OCRService:
    """FastAPI 측 OCR thin service — RQ producer + DB 영속 + 결과 폴링."""

    def __init__(self, repository: OcrDraftRepository | None = None) -> None:
        # RQ enqueue 용 sync client. keepalive 일괄 적용. 결과 저장은 DB 가
        # 담당하므로 polling/delete 용 redis client 는 불필요.
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        self._queue = Queue("ai", connection=make_sync_redis(redis_url))
        self._repository = repository or OcrDraftRepository()

    async def enqueue_ocr_task(self, file: UploadFile, profile_id: UUID | str) -> OcrExtractResponse:
        """업로드 bytes 를 ai-worker 로 enqueue 한다 (dedup 적용).

        같은 사용자 + 같은 image_hash + 미consume 인 draft 가 이미 있으면
        새 enqueue 없이 기존 draft_id 를 반환한다.

        Args:
            file: 사용자가 업로드한 처방전 이미지.
            profile_id: 업로드한 프로필 ID.

        Returns:
            ``OcrExtractResponse`` — draft_id 와 빈 medicines 리스트.
        """
        image_bytes = await file.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        filename = file.filename or "prescription.jpg"

        existing = await self._repository.find_active_by_hash(profile_id, image_hash)
        if existing is not None:
            return OcrExtractResponse(draft_id=str(existing.id), medicines=[])

        draft = await self._repository.create_pending(profile_id, image_hash, filename)
        self._queue.enqueue(_OCR_JOB_REF, image_bytes, filename, str(draft.id))
        return OcrExtractResponse(draft_id=str(draft.id), medicines=[])

    async def get_draft_data(
        self,
        draft_id: UUID | str,
        profile_id: UUID | str,
    ) -> OcrDraftPollResponse | None:
        """폴링 — DB 에서 draft 를 조회해 status + medicines 를 반환한다.

        Args:
            draft_id: enqueue 응답의 draft_id.
            profile_id: 요청자 프로필 ID (ownership 검증).

        Returns:
            ``OcrDraftPollResponse`` 또는 ``None`` (없거나 타인 소유).
        """
        draft = await self._repository.get_by_id(draft_id, profile_id)
        if draft is None:
            return None
        return _to_poll_response(draft)

    async def stream_draft_states(
        self,
        draft_id: UUID | str,
        profile_id: UUID | str,
        *,
        max_seconds: int = _STREAM_MAX_SECONDS,
        tick_seconds: float = _STREAM_TICK_SECONDS,
    ) -> AsyncIterator[str]:
        r"""SSE 스트림 — draft 상태 변화 시점마다 event 를 yield 한다.

        - 첫 호출 시 현재 상태를 즉시 1회 yield (클라이언트가 stale 응답 안 받게).
        - 이후 ``tick_seconds`` 마다 DB 재조회, 상태가 바뀌면 yield.
        - terminal 상태 (ready / no_text / no_candidates / failed) 도달 시 close.
        - ``max_seconds`` 도달 시 timeout event 후 close — 클라이언트는 다시 연결.
        - draft 가 사라지면 error event 후 close.

        Args:
            draft_id: 스트리밍할 draft ID.
            profile_id: ownership 검증용.
            max_seconds: 단일 SSE 연결 최대 유지 시간.
            tick_seconds: DB 재조회 주기.

        Yields:
            ``"event: <name>\\ndata: <json>\\n\\n"`` 형식의 SSE chunk.
        """
        deadline = time.monotonic() + max_seconds
        last_status: OcrDraftStatus | None = None
        while True:
            draft = await self._repository.get_by_id(draft_id, profile_id)
            if draft is None:
                yield _sse_event("error", {"detail": "Draft not found."})
                return

            poll = _to_poll_response(draft)
            if poll.status != last_status:
                yield _sse_event("update", poll.model_dump(mode="json"))
                last_status = poll.status

            if poll.status != OcrDraftStatus.PENDING:
                return
            if time.monotonic() >= deadline:
                yield _sse_event("timeout", {"status": poll.status.value})
                return
            await asyncio.sleep(tick_seconds)

    async def list_active_drafts(self, profile_id: UUID | str) -> OcrActiveDraftsResponse:
        """Main 페이지 카드용 — 사용자의 활성 draft 요약 목록.

        Args:
            profile_id: 요청자 프로필 ID.

        Returns:
            ``OcrActiveDraftsResponse`` — 빈 리스트일 수 있음 (초기 사용자 등).
        """
        drafts = await self._repository.list_active(profile_id)
        return OcrActiveDraftsResponse(drafts=[_to_summary(d) for d in drafts])

    async def discard_draft(self, draft_id: UUID | str, profile_id: UUID | str) -> bool:
        """사용자가 검수 화면에서 "다시 촬영" 등으로 draft 를 폐기 처리.

        ``consumed_at`` 을 설정해 active list 와 dedup 검색에서 제외시킨다
        (soft delete). row 자체는 24h 까지 보관 — 통계·감사용.

        Args:
            draft_id: 폐기할 draft ID.
            profile_id: 요청자 프로필 ID (ownership 검증).

        Returns:
            ``True`` 면 새로 폐기, ``False`` 면 이미 처리됨/없음/타인 소유.
        """
        return await self._repository.mark_consumed(draft_id, profile_id)

    async def confirm_and_save(
        self,
        request: ConfirmMedicationRequest,
        profile_id: UUID | str,
    ) -> dict[str, Any]:
        """검수 완료된 약품을 DB 에 영구 저장하고 draft 를 consume 처리.

        Args:
            request: 검수된 약품 리스트 + draft_id.
            profile_id: 요청자 프로필 ID.

        Returns:
            ``{"status": "success", "message": str}``.

        Raises:
            ValueError: draft 가 이미 처리됐거나 만료·없음·타인 소유.
        """
        consumed = await self._repository.mark_consumed(request.draft_id, profile_id)
        if not consumed:
            raise ValueError("이미 처리되었거나 만료된 처방전입니다. 새로 등록해주세요.")

        saved = [await self._save_one_medication(med, profile_id) for med in request.confirmed_medicines]
        return {
            "status": "success",
            "message": f"{len(saved)}개의 약품이 성공적으로 저장되었습니다.",
        }

    async def _save_one_medication(self, med: ExtractedMedicine, profile_id: UUID | str) -> Medication:
        """확정된 약품 한 건을 ``Medication`` 으로 저장."""
        daily_count = med.daily_intake_count or 1
        total_days = med.total_intake_days or 1
        total_count = daily_count * total_days
        today = datetime.now(tz=config.TIMEZONE).date()
        return await Medication.create(
            profile_id=str(profile_id),
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


def _to_poll_response(draft: OcrDraft) -> OcrDraftPollResponse:
    """OcrDraft → 폴링 응답 DTO 매핑."""
    return OcrDraftPollResponse(
        draft_id=str(draft.id),
        status=OcrDraftStatus(draft.status),
        medicines=[ExtractedMedicine.model_validate(m) for m in (draft.medicines or [])],
    )


def _to_summary(draft: OcrDraft) -> OcrDraftSummary:
    """OcrDraft → main 카드 summary 매핑."""
    return OcrDraftSummary(
        draft_id=str(draft.id),
        status=OcrDraftStatus(draft.status),
        created_at=draft.created_at,
    )


def _sse_event(event_name: str, data: dict[str, Any]) -> str:
    r"""SSE 한 event 를 직렬화 — ``event:`` + ``data:`` + ``\n\n`` 종료."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_name}\ndata: {payload}\n\n"
