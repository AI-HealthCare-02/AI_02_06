"""Medication repository module.

This module provides data access layer for the medications table,
handling prescription medication management operations.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from tortoise.expressions import Q

from app.models.medication import Medication


class MedicationRepository:
    """Medication database repository for prescription management."""

    async def get_by_id(self, medication_id: UUID) -> Medication | None:
        """Get medication by ID (excluding soft deleted).

        Args:
            medication_id: Medication UUID.

        Returns:
            Medication | None: Medication if found, None otherwise.
        """
        return await Medication.filter(
            id=medication_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[Medication]:
        """Get all medications for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Medication]: List of medications.
        """
        return await Medication.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).all()

    async def get_all_by_profiles(self, profile_ids: list[UUID]) -> list[Medication]:
        """Get all medications for multiple profiles.

        Args:
            profile_ids: List of profile UUIDs.

        Returns:
            list[Medication]: List of medications.
        """
        if not profile_ids:
            return []
        return await Medication.filter(
            profile_id__in=profile_ids,
            deleted_at__isnull=True,
        ).all()

    async def get_active_by_profile(self, profile_id: UUID) -> list[Medication]:
        """Get currently active medications for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Medication]: List of active medications.
        """
        today = datetime.now(tz=UTC).date()

        return (
            await Medication
            .filter(
                profile_id=profile_id,
                is_active=True,
                deleted_at__isnull=True,
            )
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .all()
        )

    async def get_inactive_by_profile(self, profile_id: UUID) -> list[Medication]:
        """프로필의 복용 완료된 약품 조회 (수동 완료 처리 or end_date 경과)"""
        today = datetime.now(tz=UTC).date()
        return (
            await Medication
            .filter(
                profile_id=profile_id,
                deleted_at__isnull=True,
            )
            .filter(Q(is_active=False) | Q(end_date__lt=today, end_date__isnull=False))
            .all()
        )

    async def create(
        self,
        profile_id: UUID,
        medicine_name: str,
        intake_times: list[str],
        total_intake_count: int,
        remaining_intake_count: int,
        start_date: date,
        dose_per_intake: str | None = None,
        intake_instruction: str | None = None,
        end_date: date | None = None,
        dispensed_date: date | None = None,
        expiration_date: date | None = None,
        prescription_image_url: str | None = None,
    ) -> Medication:
        """Create new medication.

        Args:
            profile_id: Profile UUID.
            medicine_name: Name of medication.
            intake_times: List of daily intake times.
            total_intake_count: Total prescribed intake count.
            remaining_intake_count: Remaining intake count.
            start_date: Medication start date.
            dose_per_intake: Optional dosage per intake.
            intake_instruction: Optional intake instructions.
            end_date: Optional expected end date.
            dispensed_date: Optional dispensing date.
            expiration_date: Optional expiration date.
            prescription_image_url: Optional prescription image URL.

        Returns:
            Medication: Created medication.
        """
        return await Medication.create(
            id=uuid4(),
            profile_id=profile_id,
            medicine_name=medicine_name,
            dose_per_intake=dose_per_intake,
            intake_instruction=intake_instruction,
            intake_times=intake_times,
            total_intake_count=total_intake_count,
            remaining_intake_count=remaining_intake_count,
            start_date=start_date,
            end_date=end_date,
            dispensed_date=dispensed_date,
            expiration_date=expiration_date,
            prescription_image_url=prescription_image_url,
            is_active=True,
        )

    async def update(self, medication: Medication, **kwargs) -> Medication:
        """Update medication information.

        Args:
            medication: Medication to update.
            **kwargs: Fields to update.

        Returns:
            Medication: Updated medication.
        """
        await medication.update_from_dict(kwargs).save()
        return medication

    async def soft_delete(self, medication: Medication) -> Medication:
        """Soft delete medication.

        Args:
            medication: Medication to delete.

        Returns:
            Medication: Soft deleted medication.
        """
        from app.core import config

        medication.deleted_at = datetime.now(tz=config.TIMEZONE)
        await medication.save()
        return medication
