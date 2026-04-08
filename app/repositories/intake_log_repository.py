"""
IntakeLog Repository

intake_logs 테이블 데이터 접근 계층
"""

from datetime import date, datetime, time
from uuid import UUID, uuid4

from app.models.intake_log import IntakeLog


class IntakeLogRepository:
    """IntakeLog DB 저장소"""

    async def get_by_id(self, intake_log_id: UUID) -> IntakeLog | None:
        """복용 기록 ID로 조회"""
        return await IntakeLog.filter(id=intake_log_id).first()

    async def get_by_profile_and_date(self, profile_id: UUID, scheduled_date: date) -> list[IntakeLog]:
        """프로필 ID와 날짜로 복용 기록 조회"""
        return await IntakeLog.filter(
            profile_id=profile_id,
            scheduled_date=scheduled_date,
        ).all()

    async def get_by_profiles(self, profile_ids: list[UUID]) -> list[IntakeLog]:
        """여러 프로필의 복용 기록 조회"""
        if not profile_ids:
            return []
        return await IntakeLog.filter(profile_id__in=profile_ids).all()

    async def get_by_medication(self, medication_id: UUID) -> list[IntakeLog]:
        """약품 ID로 복용 기록 조회"""
        return await IntakeLog.filter(medication_id=medication_id).all()

    async def get_pending_by_profile(self, profile_id: UUID) -> list[IntakeLog]:
        """프로필의 미복용 기록 조회"""
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
        """새 복용 기록 생성"""
        return await IntakeLog.create(
            id=uuid4(),
            medication_id=medication_id,
            profile_id=profile_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            intake_status="SCHEDULED",
        )

    async def mark_as_taken(self, intake_log: IntakeLog, taken_at: datetime | None = None) -> IntakeLog:
        """복용 완료 처리"""
        from app.core import config

        intake_log.intake_status = "TAKEN"
        intake_log.taken_at = taken_at or datetime.now(tz=config.TIMEZONE)
        await intake_log.save()
        return intake_log

    async def mark_as_skipped(self, intake_log: IntakeLog) -> IntakeLog:
        """복용 스킵 처리"""
        intake_log.intake_status = "SKIPPED"
        await intake_log.save()
        return intake_log

    async def update(self, intake_log: IntakeLog, **kwargs) -> IntakeLog:
        """복용 기록 업데이트"""
        await intake_log.update_from_dict(kwargs).save()
        return intake_log

    async def delete(self, intake_log: IntakeLog) -> None:
        """복용 기록 삭제 (hard delete)"""
        await intake_log.delete()
