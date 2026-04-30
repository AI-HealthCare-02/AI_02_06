"""Prescription group repository module.

Tortoise ORM 기반 처방전 그룹 CRUD. 그룹 자체는 OCR confirm / 수동 등록
시점에 자동 생성되며, 본 Repository 는 그 단순 INSERT 와 조회/소프트 삭제만
제공한다. medication / lifestyle_guide / challenge 의 FK 처리 로직은 각
도메인 service 가 책임.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from app.core import config
from app.models.prescription_group import PrescriptionGroup, PrescriptionGroupSource


class PrescriptionGroupRepository:
    """Prescription group database repository."""

    async def create(
        self,
        profile_id: UUID | str,
        *,
        dispensed_date: date | None,
        department: str | None,
        source: PrescriptionGroupSource = PrescriptionGroupSource.OCR,
    ) -> PrescriptionGroup:
        """Create a new prescription group.

        Args:
            profile_id: 그룹 소유 프로필 UUID.
            dispensed_date: 처방 조제일 (없으면 NULL).
            department: 진료과 (없으면 NULL).
            source: 생성 경로 — OCR / MANUAL / MIGRATED.

        Returns:
            Created PrescriptionGroup instance.
        """
        return await PrescriptionGroup.create(
            id=uuid4(),
            profile_id=str(profile_id),
            dispensed_date=dispensed_date,
            department=department,
            source=source.value,
        )

    async def get_by_id(self, group_id: UUID) -> PrescriptionGroup | None:
        """Get group by ID (excluding soft deleted)."""
        return await PrescriptionGroup.filter(
            id=group_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[PrescriptionGroup]:
        """Profile 의 모든 active 처방전 그룹 — 최근 처방일 기준 내림차순.

        dispensed_date NULL row 는 created_at 기준 정렬되도록 NULLS LAST.
        """
        return (
            await PrescriptionGroup
            .filter(
                profile_id=profile_id,
                deleted_at__isnull=True,
            )
            .order_by("-dispensed_date", "-created_at")
            .all()
        )

    async def soft_delete(self, group: PrescriptionGroup) -> PrescriptionGroup:
        """Soft delete prescription group (cascade FK 정리는 호출 측 책임)."""
        group.deleted_at = datetime.now(tz=config.TIMEZONE)
        await group.save()
        return group
