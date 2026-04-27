"""Lifestyle guide repository module.

This module provides data access layer for the lifestyle_guides table,
handling guide creation, async-pipeline state transitions and retrieval.
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.core import config
from app.models.lifestyle_guide import LifestyleGuide, LifestyleGuideStatusValue


class LifestyleGuideRepository:
    """Lifestyle guide database repository for guide management."""

    async def create(
        self,
        profile_id: UUID,
        content: dict,
        medication_snapshot: list[dict],
    ) -> LifestyleGuide:
        """Create a new ready-state lifestyle guide record (legacy/sync path).

        Kept for callers that already have GPT content in hand. The async
        pipeline uses ``create_pending`` + ``mark_ready`` instead.

        Args:
            profile_id: Owner profile UUID.
            content: GPT-generated guide content dict (5 categories).
            medication_snapshot: Active medication list serialized as dicts.

        Returns:
            LifestyleGuide: Created guide instance.
        """
        return await LifestyleGuide.create(
            id=uuid4(),
            profile_id=profile_id,
            content=content,
            medication_snapshot=medication_snapshot,
            status=LifestyleGuideStatusValue.READY.value,
            processed_at=datetime.now(tz=config.TIMEZONE),
        )

    async def create_pending(
        self,
        profile_id: UUID,
        medication_snapshot: list[dict],
    ) -> LifestyleGuide:
        """Insert a pending guide row — RQ producer 진입점.

        Status='pending', content={} 로 행을 만든다. ai-worker 가
        ``mark_ready`` 또는 ``mark_terminal`` 로 마무리한다.

        Args:
            profile_id: Owner profile UUID.
            medication_snapshot: Snapshot of active meds (이후 LLM 입력).

        Returns:
            새로 INSERT 된 ``LifestyleGuide`` 인스턴스.
        """
        return await LifestyleGuide.create(
            id=uuid4(),
            profile_id=profile_id,
            content={},
            medication_snapshot=medication_snapshot,
            status=LifestyleGuideStatusValue.PENDING.value,
        )

    async def mark_ready(self, guide_id: UUID | str, content: dict) -> int:
        """ai-worker — content 채우고 status='ready' + processed_at 기록.

        Args:
            guide_id: Pending 가이드 ID.
            content: ``LlmGuideResponse.model_dump(exclude={'recommended_challenges'})``.

        Returns:
            UPDATE 된 row 수 (정상 1, 사용자가 사이에 삭제했으면 0).
        """
        return await LifestyleGuide.filter(id=guide_id).update(
            status=LifestyleGuideStatusValue.READY.value,
            content=content,
            processed_at=datetime.now(tz=config.TIMEZONE),
        )

    async def mark_terminal(
        self,
        guide_id: UUID | str,
        status: LifestyleGuideStatusValue,
    ) -> int:
        """ai-worker — terminal status (no_active_meds / failed) 로 마감.

        ``ready`` 는 ``mark_ready`` 가 content 와 함께 처리하므로 여기 들어오면 안 된다.

        Args:
            guide_id: Pending 가이드 ID.
            status: terminal status.

        Returns:
            UPDATE 된 row 수.
        """
        return await LifestyleGuide.filter(id=guide_id).update(
            status=status.value,
            processed_at=datetime.now(tz=config.TIMEZONE),
        )

    async def get_by_id(self, guide_id: UUID) -> LifestyleGuide | None:
        """Get guide by primary key.

        Args:
            guide_id: Guide UUID.

        Returns:
            LifestyleGuide | None: Guide if found, None otherwise.
        """
        return await LifestyleGuide.filter(id=guide_id).first()

    async def get_latest_by_profile(self, profile_id: UUID) -> LifestyleGuide | None:
        """Get most recently created guide for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            LifestyleGuide | None: Latest guide or None.
        """
        return await LifestyleGuide.filter(profile_id=profile_id).order_by("-created_at").first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[LifestyleGuide]:
        """Get all guides for a profile ordered by newest first.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[LifestyleGuide]: List of guides newest first.
        """
        return await LifestyleGuide.filter(profile_id=profile_id).order_by("-created_at").all()

    async def delete_by_id(self, guide_id: UUID) -> None:
        """Hard-delete a lifestyle guide by ID.

        Args:
            guide_id: Guide UUID to delete.
        """
        await LifestyleGuide.filter(id=guide_id).delete()
