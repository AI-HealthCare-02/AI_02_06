"""
IntakeLog Service

복용 기록 관련 비즈니스 로직
"""

from datetime import date, datetime, time
from uuid import UUID

from fastapi import HTTPException, status

from app.models.intake_log import IntakeLog
from app.repositories.intake_log_repository import IntakeLogRepository
from app.repositories.profile_repository import ProfileRepository


class IntakeLogService:
    """복용 기록 비즈니스 로직"""

    def __init__(self):
        self.repository = IntakeLogRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """프로필 소유권 검증"""
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필을 찾을 수 없습니다.",
            )
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 프로필에 대한 접근 권한이 없습니다.",
            )

    async def _verify_intake_log_ownership(self, intake_log: IntakeLog, account_id: UUID) -> None:
        """복용 기록 소유권 검증 (프로필을 통해)"""
        await intake_log.fetch_related("profile")
        if intake_log.profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 복용 기록에 대한 접근 권한이 없습니다.",
            )

    async def get_intake_log(self, intake_log_id: UUID) -> IntakeLog:
        """복용 기록 조회"""
        intake_log = await self.repository.get_by_id(intake_log_id)
        if not intake_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="복용 기록을 찾을 수 없습니다.",
            )
        return intake_log

    async def get_intake_log_with_owner_check(self, intake_log_id: UUID, account_id: UUID) -> IntakeLog:
        """소유권 검증 후 복용 기록 조회"""
        intake_log = await self.get_intake_log(intake_log_id)
        await self._verify_intake_log_ownership(intake_log, account_id)
        return intake_log

    async def get_logs_by_profile_and_date(self, profile_id: UUID, target_date: date) -> list[IntakeLog]:
        """프로필의 특정 날짜 복용 기록 조회"""
        return await self.repository.get_by_profile_and_date(profile_id, target_date)

    async def get_logs_by_profile_and_date_with_owner_check(
        self, profile_id: UUID, target_date: date, account_id: UUID
    ) -> list[IntakeLog]:
        """소유권 검증 후 프로필의 특정 날짜 복용 기록 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_by_profile_and_date(profile_id, target_date)

    async def get_today_logs(self, profile_id: UUID) -> list[IntakeLog]:
        """프로필의 오늘 복용 기록 조회"""
        return await self.repository.get_by_profile_and_date(profile_id, date.today())

    async def get_today_logs_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[IntakeLog]:
        """소유권 검증 후 프로필의 오늘 복용 기록 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_by_profile_and_date(profile_id, date.today())

    async def get_logs_by_account(self, account_id: UUID) -> list[IntakeLog]:
        """계정의 모든 프로필에 해당하는 복용 기록 조회"""
        profiles = await self.profile_repository.get_all_by_account(account_id)
        profile_ids = [p.id for p in profiles]
        return await self.repository.get_by_profiles(profile_ids)

    async def get_pending_logs(self, profile_id: UUID) -> list[IntakeLog]:
        """프로필의 미복용 기록 조회"""
        return await self.repository.get_pending_by_profile(profile_id)

    async def create_intake_log(
        self,
        medication_id: UUID,
        profile_id: UUID,
        scheduled_date: date,
        scheduled_time: time,
    ) -> IntakeLog:
        """복용 기록 생성"""
        return await self.repository.create(
            medication_id=medication_id,
            profile_id=profile_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        )

    async def create_intake_log_with_owner_check(
        self,
        medication_id: UUID,
        profile_id: UUID,
        account_id: UUID,
        scheduled_date: date,
        scheduled_time: time,
    ) -> IntakeLog:
        """소유권 검증 후 복용 기록 생성"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_intake_log(
            medication_id=medication_id,
            profile_id=profile_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        )

    async def mark_as_taken(self, intake_log_id: UUID, taken_at: datetime | None = None) -> IntakeLog:
        """복용 완료 처리"""
        intake_log = await self.get_intake_log(intake_log_id)

        if intake_log.intake_status != "SCHEDULED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 복용 기록입니다.",
            )

        return await self.repository.mark_as_taken(intake_log, taken_at)

    async def mark_as_taken_with_owner_check(
        self, intake_log_id: UUID, account_id: UUID, taken_at: datetime | None = None
    ) -> IntakeLog:
        """소유권 검증 후 복용 완료 처리"""
        intake_log = await self.get_intake_log_with_owner_check(intake_log_id, account_id)

        if intake_log.intake_status != "SCHEDULED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 복용 기록입니다.",
            )

        return await self.repository.mark_as_taken(intake_log, taken_at)

    async def mark_as_skipped(self, intake_log_id: UUID) -> IntakeLog:
        """복용 스킵 처리"""
        intake_log = await self.get_intake_log(intake_log_id)

        if intake_log.intake_status != "SCHEDULED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 복용 기록입니다.",
            )

        return await self.repository.mark_as_skipped(intake_log)

    async def mark_as_skipped_with_owner_check(self, intake_log_id: UUID, account_id: UUID) -> IntakeLog:
        """소유권 검증 후 복용 스킵 처리"""
        intake_log = await self.get_intake_log_with_owner_check(intake_log_id, account_id)

        if intake_log.intake_status != "SCHEDULED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 복용 기록입니다.",
            )

        return await self.repository.mark_as_skipped(intake_log)

    async def delete_intake_log(self, intake_log_id: UUID) -> None:
        """복용 기록 삭제 (hard delete)"""
        intake_log = await self.get_intake_log(intake_log_id)
        await self.repository.delete(intake_log)

    async def delete_intake_log_with_owner_check(self, intake_log_id: UUID, account_id: UUID) -> None:
        """소유권 검증 후 복용 기록 삭제 (hard delete)"""
        intake_log = await self.get_intake_log_with_owner_check(intake_log_id, account_id)
        await self.repository.delete(intake_log)
