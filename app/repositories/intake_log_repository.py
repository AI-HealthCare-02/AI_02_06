"""Intake log repository module.

This module provides data access layer for the intake_logs table,
handling medication intake tracking operations.
"""

from datetime import date, datetime, time
from uuid import UUID, uuid4

from app.models.intake_log import IntakeLog


class IntakeLogRepository:
    """Intake log database repository for medication tracking."""

    async def get_by_id(self, intake_log_id: UUID) -> IntakeLog | None:
        """Get intake log by ID.

        Args:
            intake_log_id: Intake log UUID.

        Returns:
            IntakeLog | None: Intake log if found, None otherwise.
        """
        return await IntakeLog.filter(id=intake_log_id).first()

    async def get_by_profile_and_date(self, profile_id: UUID, scheduled_date: date) -> list[IntakeLog]:
        """Get intake logs by profile ID and date.

        Args:
            profile_id: Profile UUID.
            scheduled_date: Scheduled intake date.

        Returns:
            list[IntakeLog]: List of intake logs.
        """
        return await IntakeLog.filter(
            profile_id=profile_id,
            scheduled_date=scheduled_date,
        ).all()

    async def get_by_profiles(self, profile_ids: list[UUID]) -> list[IntakeLog]:
        """Get intake logs for multiple profiles.

        Args:
            profile_ids: List of profile UUIDs.

        Returns:
            list[IntakeLog]: List of intake logs.
        """
        if not profile_ids:
            return []
        return await IntakeLog.filter(profile_id__in=profile_ids).all()

    async def get_by_medication(self, medication_id: UUID) -> list[IntakeLog]:
        """Get intake logs by medication ID.

        Args:
            medication_id: Medication UUID.

        Returns:
            list[IntakeLog]: List of intake logs.
        """
        return await IntakeLog.filter(medication_id=medication_id).all()

    async def get_taken_dates_by_profile(self, profile_id: UUID) -> set[date]:
        """Get all dates with at least one taken intake log for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            set[date]: Set of dates with at least one TAKEN log.
        """
        dates = await IntakeLog.filter(
            profile_id=profile_id,
            intake_status="TAKEN",
        ).values_list("scheduled_date", flat=True)
        return set(dates)

    async def get_pending_by_profile(self, profile_id: UUID) -> list[IntakeLog]:
        """Get pending intake logs for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[IntakeLog]: List of pending intake logs.
        """
        return await IntakeLog.filter(
            profile_id=profile_id,
            intake_status="SCHEDULED",
        ).all()

    async def create(
        self,
        medication_id: UUID,
        profile_id: UUID,
        scheduled_date: date,
        scheduled_time: time,
    ) -> IntakeLog:
        """Create new intake log.

        Args:
            medication_id: Medication UUID.
            profile_id: Profile UUID.
            scheduled_date: Scheduled intake date.
            scheduled_time: Scheduled intake time.

        Returns:
            IntakeLog: Created intake log.
        """
        return await IntakeLog.create(
            id=uuid4(),
            medication_id=medication_id,
            profile_id=profile_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            intake_status="SCHEDULED",
        )

    async def mark_as_taken(self, intake_log: IntakeLog, taken_at: datetime | None = None) -> IntakeLog:
        """Mark intake log as taken.

        Args:
            intake_log: Intake log to update.
            taken_at: Optional taken timestamp.

        Returns:
            IntakeLog: Updated intake log.
        """
        from app.core import config

        intake_log.intake_status = "TAKEN"
        intake_log.taken_at = taken_at or datetime.now(tz=config.TIMEZONE)
        await intake_log.save()
        return intake_log

    async def mark_as_skipped(self, intake_log: IntakeLog) -> IntakeLog:
        """Mark intake log as skipped.

        Args:
            intake_log: Intake log to update.

        Returns:
            IntakeLog: Updated intake log.
        """
        intake_log.intake_status = "SKIPPED"
        await intake_log.save()
        return intake_log

    async def update(self, intake_log: IntakeLog, **kwargs) -> IntakeLog:
        """Update intake log.

        Args:
            intake_log: Intake log to update.
            **kwargs: Fields to update.

        Returns:
            IntakeLog: Updated intake log.
        """
        await intake_log.update_from_dict(kwargs).save()
        return intake_log

    async def delete(self, intake_log: IntakeLog) -> None:
        """Delete intake log (hard delete).

        Args:
            intake_log: Intake log to delete.
        """
        await intake_log.delete()
