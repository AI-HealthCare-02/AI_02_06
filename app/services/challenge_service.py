"""Challenge service module.

This module provides business logic for challenge management operations
including creation, updates, completion tracking, and ownership verification.
"""

from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException, status

from app.core import config
from app.dtos.challenge import ChallengeCreate, ChallengeUpdate
from app.models.challenge import Challenge
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.profile_repository import ProfileRepository


class ChallengeService:
    """Challenge business logic service for health challenge management."""

    def __init__(self):
        self.repository = ChallengeRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """Verify profile ownership.

        Args:
            profile_id: Profile UUID to verify.
            account_id: Account UUID that should own the profile.

        Raises:
            HTTPException: If profile not found or access denied.
        """
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this profile.",
            )

    async def _verify_challenge_ownership(self, challenge: Challenge, account_id: UUID) -> None:
        """Verify challenge ownership through profile.

        Args:
            challenge: Challenge to verify ownership for.
            account_id: Account UUID that should own the challenge.

        Raises:
            HTTPException: If access denied to challenge.
        """
        await challenge.fetch_related("profile")
        if challenge.profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this challenge.",
            )

    async def get_challenge(self, challenge_id: UUID) -> Challenge:
        """Get challenge by ID.

        Args:
            challenge_id: Challenge UUID.

        Returns:
            Challenge: Challenge object.

        Raises:
            HTTPException: If challenge not found.
        """
        challenge = await self.repository.get_by_id(challenge_id)
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found.",
            )
        return challenge

    async def get_challenge_with_owner_check(self, challenge_id: UUID, account_id: UUID) -> Challenge:
        """Get challenge with ownership verification.

        Args:
            challenge_id: Challenge UUID.
            account_id: Account UUID for ownership check.

        Returns:
            Challenge: Challenge object if owned by account.
        """
        challenge = await self.get_challenge(challenge_id)
        await self._verify_challenge_ownership(challenge, account_id)
        return challenge

    async def get_challenges_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """Get all challenges for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Challenge]: List of challenges.
        """
        return await self.repository.get_all_by_profile(profile_id)

    async def get_challenges_by_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Challenge]:
        """Get all challenges for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[Challenge]: List of challenges if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_all_by_profile(profile_id)

    async def get_active_challenges(self, profile_id: UUID) -> list[Challenge]:
        """Get active challenges for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Challenge]: List of active challenges.
        """
        return await self.repository.get_active_by_profile(profile_id)

    async def get_active_challenges_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Challenge]:
        """Get active challenges for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[Challenge]: List of active challenges if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_active_by_profile(profile_id)

    async def get_challenges_by_account(self, account_id: UUID) -> list[Challenge]:
        """Get all challenges for all profiles of an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[Challenge]: List of challenges for all account profiles.
        """
        profiles = await self.profile_repository.get_all_by_account(account_id)
        profile_ids = [p.id for p in profiles]
        return await self.repository.get_all_by_profiles(profile_ids)

    async def create_challenge(
        self,
        profile_id: UUID,
        data: ChallengeCreate,
    ) -> Challenge:
        """Create new challenge.

        Args:
            profile_id: Profile UUID.
            data: Challenge creation data.

        Returns:
            Challenge: Created challenge.
        """
        return await self.repository.create(
            profile_id=profile_id,
            title=data.title,
            description=data.description,
            target_days=data.target_days,
            started_date=data.started_date or datetime.now(tz=config.TIMEZONE).date(),
        )

    async def create_challenge_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
        data: ChallengeCreate,
    ) -> Challenge:
        """Create challenge with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.
            data: Challenge creation data.

        Returns:
            Challenge: Created challenge if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_challenge(profile_id, data)

    async def update_challenge(
        self,
        challenge_id: UUID,
        data: ChallengeUpdate,
    ) -> Challenge:
        """Update challenge.

        Args:
            challenge_id: Challenge UUID.
            data: Challenge update data.

        Returns:
            Challenge: Updated challenge.
        """
        challenge = await self.get_challenge(challenge_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(challenge, **update_data)

    async def update_challenge_with_owner_check(
        self,
        challenge_id: UUID,
        account_id: UUID,
        data: ChallengeUpdate,
    ) -> Challenge:
        """Update challenge with ownership verification.

        Args:
            challenge_id: Challenge UUID.
            account_id: Account UUID for ownership check.
            data: Challenge update data.

        Returns:
            Challenge: Updated challenge if owned by account.
        """
        challenge = await self.get_challenge_with_owner_check(challenge_id, account_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(challenge, **update_data)

    async def complete_day(
        self,
        challenge_id: UUID,
        completed_date: date | None = None,
    ) -> Challenge:
        """Mark challenge day as completed.

        Args:
            challenge_id: Challenge UUID.
            completed_date: Date to mark as completed (defaults to today).

        Returns:
            Challenge: Updated challenge with completion recorded.
        """
        challenge = await self.get_challenge(challenge_id)
        target_date = completed_date or datetime.now(tz=config.TIMEZONE).date()

        completed_dates = challenge.completed_dates or []
        if target_date.isoformat() not in completed_dates:
            completed_dates.append(target_date.isoformat())

        # Update status to completed when target is reached
        if len(completed_dates) >= challenge.target_days:
            return await self.repository.update(
                challenge,
                completed_dates=completed_dates,
                challenge_status="COMPLETED",
            )

        return await self.repository.update(challenge, completed_dates=completed_dates)

    async def delete_challenge(self, challenge_id: UUID) -> None:
        """Delete challenge (soft delete).

        Args:
            challenge_id: Challenge UUID to delete.
        """
        challenge = await self.get_challenge(challenge_id)
        await self.repository.soft_delete(challenge)

    async def delete_challenge_with_owner_check(self, challenge_id: UUID, account_id: UUID) -> None:
        """Delete challenge with ownership verification (soft delete).

        Args:
            challenge_id: Challenge UUID to delete.
            account_id: Account UUID for ownership check.
        """
        challenge = await self.get_challenge_with_owner_check(challenge_id, account_id)
        await self.repository.soft_delete(challenge)
