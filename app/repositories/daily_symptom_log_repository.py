"""Daily symptom log repository module.

This module provides data access layer for the daily_symptom_logs table,
handling creation and retrieval of user-reported symptom entries.
"""

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from app.core import config
from app.models.daily_symptom_log import DailySymptomLog


class DailySymptomLogRepository:
    """Daily symptom log database repository."""

    async def create(
        self,
        profile_id: UUID,
        log_date: date,
        symptoms: list[str],
        note: str | None = None,
    ) -> DailySymptomLog:
        """Create a new daily symptom log entry.

        Args:
            profile_id: Owner profile UUID.
            log_date: Date of the symptom report.
            symptoms: List of reported symptom strings.
            note: Optional free-text note.

        Returns:
            DailySymptomLog: Created log instance.
        """
        return await DailySymptomLog.create(
            id=uuid4(),
            profile_id=profile_id,
            log_date=log_date,
            symptoms=symptoms,
            note=note,
        )

    async def get_recent_by_profile(
        self,
        profile_id: UUID,
        days: int,
    ) -> list[DailySymptomLog]:
        """Get symptom logs for the past N days for a profile.

        Args:
            profile_id: Profile UUID.
            days: Number of days to look back from today.

        Returns:
            list[DailySymptomLog]: Logs ordered newest first.
        """
        cutoff = datetime.now(tz=config.TIMEZONE).date() - timedelta(days=days)
        return (
            await DailySymptomLog
            .filter(
                profile_id=profile_id,
                log_date__gte=cutoff,
            )
            .order_by("-log_date")
            .all()
        )

    async def bulk_delete_by_profile(self, profile_id: UUID) -> int:
        """프로필의 모든 daily symptom log 일괄 hard-delete.

        DailySymptomLog 는 deleted_at 컬럼이 없는 일별 누적 로그라 hard-delete
        정책. Profile cascade soft-delete 흐름의 일부로 호출.

        Args:
            profile_id: 대상 프로필 UUID.

        Returns:
            삭제된 row 수.
        """
        return await DailySymptomLog.filter(profile_id=profile_id).delete()
