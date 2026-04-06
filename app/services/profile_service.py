"""
Profile Service

프로필 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.profile import ProfileCreate, ProfileUpdate
from app.models.profiles import Profile, RelationType
from app.repositories.profile_repository import ProfileRepository


class ProfileService:
    """프로필 비즈니스 로직"""

    def __init__(self):
        self.repository = ProfileRepository()

    async def get_profile(self, profile_id: UUID) -> Profile:
        """프로필 조회"""
        profile = await self.repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필을 찾을 수 없습니다.",
            )
        return profile

    async def get_profiles_by_account(self, account_id: UUID) -> list[Profile]:
        """계정의 모든 프로필 조회"""
        return await self.repository.get_all_by_account(account_id)

    async def get_self_profile(self, account_id: UUID) -> Profile | None:
        """계정의 본인 프로필 조회"""
        return await self.repository.get_self_profile(account_id)

    async def create_profile(
        self,
        account_id: UUID,
        data: ProfileCreate,
    ) -> Profile:
        """프로필 생성"""
        relation_type = RelationType(data.relation_type)

        # SELF 프로필은 계정당 하나만 허용
        if relation_type == RelationType.SELF:
            existing_self = await self.repository.get_self_profile(account_id)
            if existing_self:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="본인 프로필은 이미 존재합니다.",
                )

        return await self.repository.create(
            account_id=account_id,
            name=data.name,
            relation_type=relation_type,
            health_survey=data.health_survey,
        )

    async def update_profile(
        self,
        profile_id: UUID,
        data: ProfileUpdate,
    ) -> Profile:
        """프로필 수정"""
        profile = await self.get_profile(profile_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(profile, **update_data)

    async def delete_profile(self, profile_id: UUID) -> None:
        """프로필 삭제 (soft delete)"""
        profile = await self.get_profile(profile_id)
        await self.repository.soft_delete(profile)
