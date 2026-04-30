"""Profile repository module.

This module provides data access layer for the profiles table,
handling user and family member profile management operations.
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.core import config
from app.models.profiles import Profile, RelationType


class ProfileRepository:
    """Profile database repository for user profile management."""

    async def get_by_id(self, profile_id: UUID) -> Profile | None:
        """Get profile by ID (excluding soft deleted).

        Args:
            profile_id: Profile UUID.

        Returns:
            Profile | None: Profile if found, None otherwise.
        """
        return await Profile.filter(
            id=profile_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_account(self, account_id: UUID) -> list[Profile]:
        """Get all profiles for an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[Profile]: List of profiles.
        """
        return await Profile.filter(
            account_id=account_id,
            deleted_at__isnull=True,
        ).all()

    async def get_self_profile(self, account_id: UUID) -> Profile | None:
        """Get account's self profile.

        Args:
            account_id: Account UUID.

        Returns:
            Profile | None: Self profile if found, None otherwise.
        """
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
        """Create new profile.

        Args:
            account_id: Account UUID.
            name: Profile name.
            relation_type: Relationship type.
            health_survey: Optional health survey data.

        Returns:
            Profile: Created profile.
        """
        return await Profile.create(
            id=uuid4(),
            account_id=account_id,
            name=name,
            relation_type=relation_type,
            health_survey=health_survey,
        )

    async def update(self, profile: Profile, **kwargs) -> Profile:
        """Update profile information.

        Args:
            profile: Profile to update.
            **kwargs: Fields to update.

        Returns:
            Profile: Updated profile.
        """
        await profile.update_from_dict(kwargs).save()
        return profile

    async def soft_delete(self, profile: Profile) -> Profile:
        """Soft delete profile.

        Args:
            profile: Profile to delete.

        Returns:
            Profile: Soft deleted profile.
        """
        profile.deleted_at = datetime.now(tz=config.TIMEZONE)
        await profile.save()
        return profile

    async def bulk_soft_delete_by_account(self, account_id: UUID) -> int:
        """계정 소유의 모든 active profile 을 일괄 soft delete.

        회원탈퇴(account cascade soft-delete) 흐름의 1단계로 호출되며, 이미
        deleted_at 이 set 된 row 는 자연스럽게 제외된다 (idempotent).

        Args:
            account_id: 대상 계정 UUID.

        Returns:
            새로 deleted_at 이 채워진 row 수 (이미 삭제된 행은 카운트 X).
        """
        return await Profile.filter(
            account_id=account_id,
            deleted_at__isnull=True,
        ).update(deleted_at=datetime.now(tz=config.TIMEZONE))
