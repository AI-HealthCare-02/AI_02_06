"""Lifestyle guide service — RQ producer + SSE long-poll thin layer.

본 서비스는 더 이상 LLM 을 직접 호출하지 않는다. ``generate_guide`` 가
``lifestyle_guides`` 에 pending row 를 INSERT 하고 RQ ``ai`` 큐에
``ai_worker.domains.lifestyle.jobs.process_lifestyle_guide_task`` 를 enqueue
한 뒤 즉시 ``LifestyleGuide`` (status='pending') 를 반환한다. 이후
``stream_guide_states`` 가 SSE 로 status 변화를 push 한다.

ai-worker 가 ``content`` 를 채우고 status='ready' 로 UPDATE 하면 GET
``/lifestyle-guides/{id}`` 또는 SSE 가 곧바로 ready payload 를 응답한다.
"""

import asyncio
from collections.abc import AsyncIterator
import json
import logging
import os
import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from rq import Queue

from app.core.redis_client import make_sync_redis
from app.dtos.lifestyle_guide import LifestyleGuideStatus
from app.models.challenge import Challenge
from app.models.lifestyle_guide import LifestyleGuide
from app.models.medication import Medication
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.lifestyle_guide_repository import LifestyleGuideRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.profile_repository import ProfileRepository

logger = logging.getLogger(__name__)

_GUIDE_JOB_REF = "ai_worker.domains.lifestyle.jobs.process_lifestyle_guide_task"

# SSE long-polling — nginx default proxy_read_timeout(60s) 안에 close
_STREAM_MAX_SECONDS = 50
_STREAM_TICK_SECONDS = 0.5


def _med_to_dict(med: Medication) -> dict:
    """Medication ORM -> snapshot-safe dict (LLM prompt + DB JSONField 공용)."""
    return {
        "medicine_name": med.medicine_name,
        "category": getattr(med, "category", None),
        "intake_instruction": getattr(med, "intake_instruction", None),
        "dose_per_intake": getattr(med, "dose_per_intake", None),
    }


class LifestyleGuideService:
    """RQ producer + SSE consumer 측 thin service."""

    def __init__(self) -> None:
        self.medication_repo = MedicationRepository()
        self.guide_repo = LifestyleGuideRepository()
        self.challenge_repo = ChallengeRepository()
        self.profile_repo = ProfileRepository()

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        self._queue = Queue("ai", connection=make_sync_redis(redis_url))

    # ── 가이드 생성 (RQ producer) ─────────────────────────────────────────
    # 흐름: 활성 약물 조회 -> snapshot 직렬화 -> pending row INSERT
    #       -> RQ enqueue (ai-worker 가 LLM 호출) -> pending guide 반환
    async def enqueue_guide_generation(self, profile_id: UUID) -> LifestyleGuide:
        """활성 약물을 snapshot 으로 묶어 pending guide + RQ task 를 등록.

        Args:
            profile_id: 가이드 받을 프로필 UUID.

        Returns:
            ``LifestyleGuide`` (status='pending'). 프론트는 ``id`` 로 SSE 연결.

        Raises:
            ValueError: 활성 약물이 없으면 (LLM 호출 자체 무의미 — pre-check).
        """
        meds = await self.medication_repo.get_active_by_profile(profile_id)
        if not meds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="활성 약물이 없어 가이드를 생성할 수 없습니다. 복용 중인 약물을 먼저 등록해주세요.",
            )

        snapshot = [_med_to_dict(m) for m in meds]
        guide = await self.guide_repo.create_pending(profile_id=profile_id, medication_snapshot=snapshot)
        self._queue.enqueue(_GUIDE_JOB_REF, str(guide.id), str(profile_id))
        logger.info("[GUIDE] enqueued guide_id=%s profile_id=%s meds=%d", guide.id, profile_id, len(meds))
        return guide

    # ── SSE 스트림 ─────────────────────────────────────────────────────────
    # 흐름: deadline 설정 -> tick 마다 DB 조회 -> status 변경 시 yield
    #       -> terminal/timeout 도달 시 close
    async def stream_guide_states(
        self,
        guide_id: UUID | str,
        account_id: UUID,
        *,
        max_seconds: int = _STREAM_MAX_SECONDS,
        tick_seconds: float = _STREAM_TICK_SECONDS,
    ) -> AsyncIterator[str]:
        r"""SSE 스트림 — guide status 변화 시점마다 event yield.

        - 첫 호출 즉시 1회 update event.
        - terminal (ready / no_active_meds / failed) 도달 시 close.
        - ``max_seconds`` 도달 시 timeout event 후 close.
        - guide 가 사라지면 error event 후 close.

        Args:
            guide_id: 스트리밍할 guide ID.
            account_id: ownership 검증용 (소유자 아니면 error 후 close).
            max_seconds: 단일 SSE 연결 최대 유지 시간.
            tick_seconds: DB 재조회 주기.

        Yields:
            ``"event: <name>\\ndata: <json>\\n\\n"`` 형식의 SSE chunk.
        """
        deadline = time.monotonic() + max_seconds
        last_status: str | None = None
        while True:
            guide = await self.guide_repo.get_by_id(guide_id)  # type: ignore[arg-type]
            if guide is None:
                yield _sse_event("error", {"detail": "Guide not found."})
                return
            if not await self._is_owned_by(guide, account_id):
                yield _sse_event("error", {"detail": "Access denied."})
                return

            payload = _to_sse_payload(guide)
            if guide.status != last_status:
                yield _sse_event("update", payload)
                last_status = guide.status

            if guide.status != LifestyleGuideStatus.PENDING.value:
                return
            if time.monotonic() >= deadline:
                yield _sse_event("timeout", {"status": guide.status})
                return
            await asyncio.sleep(tick_seconds)

    # ── ownership helpers ─────────────────────────────────────────────────
    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        if profile.account_id != account_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this profile.")

    async def _verify_guide_ownership(self, guide: LifestyleGuide, account_id: UUID) -> None:
        if not await self._is_owned_by(guide, account_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this guide.")

    async def _is_owned_by(self, guide: LifestyleGuide, account_id: UUID) -> bool:
        profile = await self.profile_repo.get_by_id(guide.profile_id)
        return bool(profile and profile.account_id == account_id)

    # ── 외부 API ──────────────────────────────────────────────────────────
    async def enqueue_guide_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> LifestyleGuide:
        """생성 요청 — ownership 검증 후 enqueue. pending guide 반환."""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.enqueue_guide_generation(profile_id)

    async def get_guide_with_owner_check(self, guide_id: UUID, account_id: UUID) -> LifestyleGuide:
        guide = await self.guide_repo.get_by_id(guide_id)
        if not guide:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lifestyle guide not found.")
        await self._verify_guide_ownership(guide, account_id)
        return guide

    async def get_latest_guide_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> LifestyleGuide:
        await self._verify_profile_ownership(profile_id, account_id)
        guide = await self.guide_repo.get_latest_by_profile(profile_id)
        if not guide:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No lifestyle guide found for this profile.",
            )
        return guide

    async def list_guides_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> list[LifestyleGuide]:
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.guide_repo.get_all_by_profile(profile_id)

    async def delete_guide_with_owner_check(self, guide_id: UUID, account_id: UUID) -> None:
        """가이드 삭제 — 활성/완료 챌린지는 보존(guide_id=None), 미시작은 soft delete."""
        guide = await self.get_guide_with_owner_check(guide_id, account_id)
        challenges = await self.challenge_repo.get_by_guide_id(guide.id)
        for c in challenges:
            if not c.is_active:
                await self.challenge_repo.soft_delete(c)
            else:
                await Challenge.filter(id=c.id).update(guide_id=None)
        await self.guide_repo.delete_by_id(guide.id)
        logger.info("[GUIDE] 가이드 삭제 완료 guide_id=%s account_id=%s", guide_id, account_id)

    async def get_guide_challenges_with_owner_check(
        self,
        guide_id: UUID,
        account_id: UUID,
    ) -> list[Challenge]:
        guide = await self.guide_repo.get_by_id(guide_id)
        if not guide:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lifestyle guide not found.")
        await self._verify_guide_ownership(guide, account_id)
        return await self.challenge_repo.get_by_guide_id(guide.id)


def _to_sse_payload(guide: LifestyleGuide) -> dict[str, Any]:
    """SSE update event 의 data — LifestyleGuideResponse 와 호환되는 dict."""
    return {
        "id": str(guide.id),
        "profile_id": str(guide.profile_id),
        "status": guide.status,
        "content": guide.content or {},
        "medication_snapshot": guide.medication_snapshot or [],
        "created_at": guide.created_at.isoformat() if guide.created_at else None,
        "processed_at": guide.processed_at.isoformat() if guide.processed_at else None,
    }


def _sse_event(event_name: str, data: dict[str, Any]) -> str:
    r"""SSE 한 event 를 직렬화 — ``event:`` + ``data:`` + ``\n\n`` 종료."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_name}\ndata: {payload}\n\n"
