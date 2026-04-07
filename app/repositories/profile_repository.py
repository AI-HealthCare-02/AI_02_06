"""
Profile Repository

profiles 테이블 데이터 접근 계층
"""

from uuid import UUID, uuid4

from app.models.profiles import Profile, RelationType


class ProfileRepository:
    """Profile DB 저장소"""

    async def get_by_id(self, profile_id: UUID) -> Profile | None:
        """프로필 ID로 조회 (soft delete 제외)"""
        return await Profile.filter(
            id=profile_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_account(self, account_id: UUID) -> list[Profile]:
        """계정의 모든 프로필 조회"""
        return await Profile.filter(
            account_id=account_id,
            deleted_at__isnull=True,
        ).all()

    async def get_self_profile(self, account_id: UUID) -> Profile | None:
        """계정의 본인 프로필 조회"""
        return await Profile.filter(
            account_id=account_id,
            relation_type=RelationType.SELF,
            deleted_at__isnull=True,
        ).first()

    async def create(
        self,
        account_id: UUID,
        name: str,
        relation_type: RelationType,
        health_survey: dict | None = None,
    ) -> Profile:
        """새 프로필 생성"""
        return await Profile.create(
            id=uuid4(),
            account_id=account_id,
            name=name,
            relation_type=relation_type,
            health_survey=health_survey,
        )

    async def update(self, profile: Profile, **kwargs) -> Profile:
        """프로필 정보 업데이트"""
        await profile.update_from_dict(kwargs).save()
        return profile

    async def soft_delete(self, profile: Profile) -> Profile:
        """프로필 소프트 삭제"""
        from datetime import datetime

        from app.core import config

        profile.deleted_at = datetime.now(tz=config.TIMEZONE)
        await profile.save()
        return profile
