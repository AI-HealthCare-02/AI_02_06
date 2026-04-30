"""Challenge repository module.

This module provides data access layer for the challenges table,
handling user health challenge tracking operations.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from app.core import config
from app.dtos.lifestyle_guide import RecommendedChallenge
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

    async def get_by_guide_id(self, guide_id: UUID) -> list[Challenge]:
        """Get all challenges linked to a specific lifestyle guide.

        Args:
            guide_id: LifestyleGuide UUID.

        Returns:
            list[Challenge]: List of challenges for the guide.
        """
        return await Challenge.filter(
            guide_id=guide_id,
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
            difficulty: Optional difficulty level (쉬움/보통/어려움).

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

    async def bulk_create_from_guide(
        self,
        guide_id: UUID,
        profile_id: UUID,
        challenges: list[RecommendedChallenge],
    ) -> list[Challenge]:
        """Bulk create LLM-recommended challenges tied to a guide.

        All created challenges start with is_active=False (pending user activation).

        Args:
            guide_id: Source LifestyleGuide UUID.
            profile_id: Owner profile UUID.
            challenges: Parsed recommended challenge list from LLM response.

        Returns:
            list[Challenge]: List of created challenge instances.
        """
        today = datetime.now(tz=config.TIMEZONE).date()
        created: list[Challenge] = []
        for ch in challenges:
            challenge = await Challenge.create(
                id=uuid4(),
                profile_id=profile_id,
                guide_id=guide_id,
                category=ch.category,
                title=ch.title,
                description=ch.description,
                target_days=ch.target_days,
                difficulty=ch.difficulty,
                started_date=today,
                completed_dates=[],
                challenge_status="IN_PROGRESS",
                is_active=False,
            )
            created.append(challenge)
        return created

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
        challenge.deleted_at = datetime.now(tz=config.TIMEZONE)
        await challenge.save()
        return challenge

    async def bulk_soft_delete_by_profile(self, profile_id: UUID) -> int:
        """프로필의 모든 active challenge 를 일괄 soft delete.

        Profile cascade soft-delete 흐름에서 호출. 이미 deleted_at 이 set
        된 row 는 자연스럽게 제외 (idempotent).

        Args:
            profile_id: 대상 프로필 UUID.

        Returns:
            새로 deleted_at 이 채워진 row 수.
        """
        return await Challenge.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).update(deleted_at=datetime.now(tz=config.TIMEZONE))
