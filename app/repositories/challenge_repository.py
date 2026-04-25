"""Challenge repository module.

This module provides data access layer for the challenges table,
handling user health challenge tracking operations.
"""

from datetime import date
from uuid import UUID, uuid4

from app.models.challenge import Challenge


class ChallengeRepository:
    """Challenge database repository for health challenge management."""

    async def get_by_id(self, challenge_id: UUID) -> Challenge | None:
        """Get challenge by ID (excluding soft deleted).

        Args:
            challenge_id: Challenge UUID.

        Returns:
            Challenge | None: Challenge if found, None otherwise.
        """
        return await Challenge.filter(
            id=challenge_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """Get all challenges for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Challenge]: List of challenges.
        """
        return await Challenge.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).all()

    async def get_all_by_profiles(self, profile_ids: list[UUID]) -> list[Challenge]:
        """Get all challenges for multiple profiles.

        Args:
            profile_ids: List of profile UUIDs.

        Returns:
            list[Challenge]: List of challenges.
        """
        if not profile_ids:
            return []
        return await Challenge.filter(
            profile_id__in=profile_ids,
            deleted_at__isnull=True,
        ).all()

    async def get_active_by_profile(self, profile_id: UUID) -> list[Challenge]:
        """Get active challenges for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Challenge]: List of active challenges.
        """
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
        """Create new challenge.

        Args:
            profile_id: Profile UUID.
            title: Challenge title.
            target_days: Target completion days.
            started_date: Challenge start date.
            description: Optional challenge description.
            difficulty: Optional difficulty level.

        Returns:
            Challenge: Created challenge.
        """
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
        """Update challenge information.

        Args:
            challenge: Challenge to update.
            **kwargs: Fields to update.

        Returns:
            Challenge: Updated challenge.
        """
        await challenge.update_from_dict(kwargs).save()
        return challenge

    async def soft_delete(self, challenge: Challenge) -> Challenge:
        """Soft delete challenge.

        Args:
            challenge: Challenge to delete.

        Returns:
            Challenge: Soft deleted challenge.
        """
        from datetime import datetime

        from app.core import config

        challenge.deleted_at = datetime.now(tz=config.TIMEZONE)
        await challenge.save()
        return challenge
