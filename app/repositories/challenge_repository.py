"""
Challenge Repository

challenges 테이블 데이터 접근 계층
"""

from datetime import date
from uuid import UUID, uuid4

from app.models.challenge import Challenge


class ChallengeRepository:
    """Challenge DB 저장소"""

    async def get_by_id(self, challenge_id: UUID) -> Challenge | None:
        """챌린지 ID로 조회 (soft delete 제외)"""
        return await Challenge.filter(
            id=challenge_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """프로필의 모든 챌린지 조회"""
        return await Challenge.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).all()

    async def get_all_by_profiles(self, profile_ids: list[UUID]) -> list[Challenge]:
        """여러 프로필의 모든 챌린지 조회"""
        if not profile_ids:
            return []
        return await Challenge.filter(
            profile_id__in=profile_ids,
            deleted_at__isnull=True,
        ).all()

    async def get_active_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """프로필의 진행 중인 챌린지 조회"""
        return await Challenge.filter(
            profile_id=profile_id,
            challenge_status="IN_PROGRESS",
            deleted_at__isnull=True,
        ).all()

    async def create(
        self,
        profile_id: UUID,
        title: str,
        target_days: int,
        started_date: date,
        description: str | None = None,
        difficulty: str | None = None,
    ) -> Challenge:
        """새 챌린지 생성"""
        return await Challenge.create(
            id=uuid4(),
            profile_id=profile_id,
            title=title,
            description=description,
            target_days=target_days,
            difficulty=difficulty,
            started_date=started_date,
            completed_dates=[],
            challenge_status="IN_PROGRESS",
        )

    async def update(self, challenge: Challenge, **kwargs) -> Challenge:
        """챌린지 정보 업데이트"""
        await challenge.update_from_dict(kwargs).save()
        return challenge

    async def soft_delete(self, challenge: Challenge) -> Challenge:
        """챌린지 소프트 삭제"""
        from datetime import datetime

        from app.core import config

        challenge.deleted_at = datetime.now(tz=config.TIMEZONE)
        await challenge.save()
        return challenge
