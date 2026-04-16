"""
Challenge Service

챌린지 관련 비즈니스 로직
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.challenge import ChallengeCreate, ChallengeUpdate
from app.models.challenge import Challenge
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.profile_repository import ProfileRepository


class ChallengeService:
    """챌린지 비즈니스 로직"""

    def __init__(self):
        self.repository = ChallengeRepository()
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

    async def _verify_challenge_ownership(self, challenge: Challenge, account_id: UUID) -> None:
        """챌린지 소유권 검증 (프로필을 통해)"""
        await challenge.fetch_related("profile")
        if challenge.profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 챌린지에 대한 접근 권한이 없습니다.",
            )

    async def get_challenge(self, challenge_id: UUID) -> Challenge:
        """챌린지 조회"""
        challenge = await self.repository.get_by_id(challenge_id)
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="챌린지를 찾을 수 없습니다.",
            )
        return challenge

    async def get_challenge_with_owner_check(self, challenge_id: UUID, account_id: UUID) -> Challenge:
        """소유권 검증 후 챌린지 조회"""
        challenge = await self.get_challenge(challenge_id)
        await self._verify_challenge_ownership(challenge, account_id)
        return challenge

    async def get_challenges_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """프로필의 모든 챌린지 조회"""
        return await self.repository.get_all_by_profile(profile_id)

    async def get_challenges_by_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Challenge]:
        """소유권 검증 후 프로필의 모든 챌린지 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_all_by_profile(profile_id)

    async def get_active_challenges(self, profile_id: UUID) -> list[Challenge]:
        """프로필의 진행 중인 챌린지 조회"""
        return await self.repository.get_active_by_profile(profile_id)

    async def get_active_challenges_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Challenge]:
        """소유권 검증 후 프로필의 진행 중인 챌린지 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_active_by_profile(profile_id)

    async def get_challenges_by_account(self, account_id: UUID) -> list[Challenge]:
        """계정의 모든 프로필에 해당하는 챌린지 조회"""
        profiles = await self.profile_repository.get_all_by_account(account_id)
        profile_ids = [p.id for p in profiles]
        return await self.repository.get_all_by_profiles(profile_ids)

    async def create_challenge(
        self,
        profile_id: UUID,
        data: ChallengeCreate,
    ) -> Challenge:
        """챌린지 생성"""
        return await self.repository.create(
            profile_id=profile_id,
            title=data.title,
            description=data.description,
            target_days=data.target_days,
            difficulty=data.difficulty,
            started_date=data.started_date or date.today(),
        )

    async def create_challenge_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
        data: ChallengeCreate,
    ) -> Challenge:
        """소유권 검증 후 챌린지 생성"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_challenge(profile_id, data)

    async def update_challenge(
        self,
        challenge_id: UUID,
        data: ChallengeUpdate,
    ) -> Challenge:
        """챌린지 수정"""
        challenge = await self.get_challenge(challenge_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(challenge, **update_data)

    async def update_challenge_with_owner_check(
        self,
        challenge_id: UUID,
        account_id: UUID,
        data: ChallengeUpdate,
    ) -> Challenge:
        """소유권 검증 후 챌린지 수정"""
        challenge = await self.get_challenge_with_owner_check(challenge_id, account_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(challenge, **update_data)

    async def complete_day(
        self,
        challenge_id: UUID,
        completed_date: date | None = None,
    ) -> Challenge:
        """챌린지 하루 완료 기록"""
        challenge = await self.get_challenge(challenge_id)
        target_date = completed_date or date.today()

        completed_dates = challenge.completed_dates or []
        if target_date.isoformat() not in completed_dates:
            completed_dates.append(target_date.isoformat())

        # 목표 달성 시 상태 변경
        if len(completed_dates) >= challenge.target_days:
            return await self.repository.update(
                challenge,
                completed_dates=completed_dates,
                challenge_status="COMPLETED",
            )

        return await self.repository.update(challenge, completed_dates=completed_dates)

    async def delete_challenge(self, challenge_id: UUID) -> None:
        """챌린지 삭제 (soft delete)"""
        challenge = await self.get_challenge(challenge_id)
        await self.repository.soft_delete(challenge)

    async def delete_challenge_with_owner_check(self, challenge_id: UUID, account_id: UUID) -> None:
        """소유권 검증 후 챌린지 삭제 (soft delete)"""
        challenge = await self.get_challenge_with_owner_check(challenge_id, account_id)
        await self.repository.soft_delete(challenge)
