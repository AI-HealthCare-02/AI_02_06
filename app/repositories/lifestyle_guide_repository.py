"""Lifestyle guide repository module.

This module provides data access layer for the lifestyle_guides table,
handling guide creation and retrieval operations.
"""

from uuid import UUID, uuid4

from app.models.lifestyle_guide import LifestyleGuide


class LifestyleGuideRepository:
    """Lifestyle guide database repository for guide management."""

    async def create(
        self,
        profile_id: UUID,
        content: dict,
        medication_snapshot: list[dict],
    ) -> LifestyleGuide:
        """Create a new lifestyle guide record.

        Args:
            profile_id: Owner profile UUID.
            content: GPT-generated guide content dict (5 categories).
            medication_snapshot: Active medication list serialized as dicts.

        Returns:
            LifestyleGuide: Created guide instance.
        """
        return await LifestyleGuide.create(
            id=uuid4(),
            profile_id=profile_id,
            content=content,
            medication_snapshot=medication_snapshot,
        )

    async def get_by_id(self, guide_id: UUID) -> LifestyleGuide | None:
        """Get guide by primary key.

        Args:
            guide_id: Guide UUID.

        Returns:
            LifestyleGuide | None: Guide if found, None otherwise.
        """
        return await LifestyleGuide.filter(id=guide_id).first()

    async def get_latest_by_profile(self, profile_id: UUID) -> LifestyleGuide | None:
        """Get most recently created guide for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            LifestyleGuide | None: Latest guide or None.
        """
        return await LifestyleGuide.filter(profile_id=profile_id).order_by("-created_at").first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[LifestyleGuide]:
        """Get all guides for a profile ordered by newest first.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[LifestyleGuide]: List of guides newest first.
        """
        return await LifestyleGuide.filter(profile_id=profile_id).order_by("-created_at").all()
