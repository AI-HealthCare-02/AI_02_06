"""Profile service module.

This module provides business logic for user profile management operations
including creation, updates, and ownership verification.
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.profile import ProfileCreate, ProfileUpdate
from app.models.profiles import Profile, RelationType
from app.repositories.profile_repository import ProfileRepository


class ProfileService:
    """Profile business logic service for user profile management."""

    def __init__(self):
        self.repository = ProfileRepository()

    async def get_profile(self, profile_id: UUID) -> Profile:
        """Get profile by ID.

        Args:
            profile_id: Profile UUID.

        Returns:
            Profile: Profile object.

        Raises:
            HTTPException: If profile not found.
        """
        profile = await self.repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        return profile

    async def get_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> Profile:
        """Get profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            Profile: Profile if owned by account.

        Raises:
            HTTPException: If access denied to profile.
        """
        profile = await self.get_profile(profile_id)
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this profile.",
            )
        return profile

    async def get_profiles_by_account(self, account_id: UUID) -> list[Profile]:
        """Get all profiles for an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[Profile]: List of profiles.
        """
        return await self.repository.get_all_by_account(account_id)

    async def get_self_profile(self, account_id: UUID) -> Profile | None:
        """Get account's self profile.

        Args:
            account_id: Account UUID.

        Returns:
            Profile | None: Self profile if found, None otherwise.
        """
        return await self.repository.get_self_profile(account_id)

    async def create_profile(
        self,
        account_id: UUID,
        data: ProfileCreate,
    ) -> Profile:
        """Create new profile.

        Args:
            account_id: Account UUID.
            data: Profile creation data.

        Returns:
            Profile: Created profile.

        Raises:
            HTTPException: If SELF profile already exists for account.
        """
        relation_type = RelationType(data.relation_type)

        # Only one SELF profile allowed per account
        if relation_type == RelationType.SELF:
            existing_self = await self.repository.get_self_profile(account_id)
            if existing_self:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Self profile already exists.",
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
        """Update profile.

        Args:
            profile_id: Profile UUID.
            data: Profile update data.

        Returns:
            Profile: Updated profile.
        """
        profile = await self.get_profile(profile_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(profile, **update_data)

    async def update_profile_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
        data: ProfileUpdate,
    ) -> Profile:
        """Update profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.
            data: Profile update data.

        Returns:
            Profile: Updated profile if owned by account.
        """
        profile = await self.get_profile_with_owner_check(profile_id, account_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(profile, **update_data)

    async def delete_profile(self, profile_id: UUID) -> None:
        """Delete profile (soft delete).

        Args:
            profile_id: Profile UUID to delete.
        """
        profile = await self.get_profile(profile_id)
        await self.repository.soft_delete(profile)

    async def delete_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> None:
        """Delete profile with ownership verification (soft delete).

        SELF 프로필은 계정 자체와 묶여 있어 삭제 금지 — 계정 탈퇴 흐름으로만 제거.

        Args:
            profile_id: Profile UUID to delete.
            account_id: Account UUID for ownership check.

        Raises:
            HTTPException: 403 if profile is SELF.
        """
        profile = await self.get_profile_with_owner_check(profile_id, account_id)
        if profile.relation_type == RelationType.SELF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete SELF profile. Use account withdrawal instead.",
            )
        await self.repository.soft_delete(profile)
