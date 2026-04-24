"""Lifestyle guide API router module.

This module contains HTTP endpoints for lifestyle guide operations
including guide generation, retrieval, and associated challenge listing.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.challenge import ChallengeResponse
from app.dtos.lifestyle_guide import LifestyleGuideResponse
from app.models.accounts import Account
from app.services.lifestyle_guide_service import LifestyleGuideService

router = APIRouter(prefix="/lifestyle-guides", tags=["Lifestyle Guides"])


def get_lifestyle_guide_service() -> LifestyleGuideService:
    """Get lifestyle guide service instance.

    Returns:
        LifestyleGuideService: Lifestyle guide service instance.
    """
    return LifestyleGuideService()


# Type aliases for dependency injection
LifestyleGuideServiceDep = Annotated[LifestyleGuideService, Depends(get_lifestyle_guide_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/generate",
    response_model=LifestyleGuideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate lifestyle guide",
)
async def generate_guide(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuideResponse:
    """Generate a personalized lifestyle guide for a profile via LLM.

    Args:
        profile_id: Target profile UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.

    Returns:
        LifestyleGuideResponse: Newly created lifestyle guide.
    """
    guide = await service.generate_guide_with_owner_check(profile_id, current_account.id)
    return LifestyleGuideResponse.model_validate(guide)


@router.get(
    "/latest",
    response_model=LifestyleGuideResponse,
    summary="Get latest lifestyle guide",
)
async def get_latest_guide(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuideResponse:
    """Get the most recent lifestyle guide for a profile.

    Args:
        profile_id: Target profile UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.

    Returns:
        LifestyleGuideResponse: Latest lifestyle guide.
    """
    guide = await service.get_latest_guide_with_owner_check(profile_id, current_account.id)
    return LifestyleGuideResponse.model_validate(guide)


@router.get(
    "",
    response_model=list[LifestyleGuideResponse],
    summary="List lifestyle guides",
)
async def list_guides(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> list[LifestyleGuideResponse]:
    """List all lifestyle guides for a profile.

    Args:
        profile_id: Target profile UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.

    Returns:
        list[LifestyleGuideResponse]: Guides ordered newest first.
    """
    guides = await service.list_guides_with_owner_check(profile_id, current_account.id)
    return [LifestyleGuideResponse.model_validate(g) for g in guides]


@router.get(
    "/{guide_id}",
    response_model=LifestyleGuideResponse,
    summary="Get lifestyle guide details",
)
async def get_guide(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuideResponse:
    """Get detailed information about a specific lifestyle guide.

    Args:
        guide_id: Guide UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.

    Returns:
        LifestyleGuideResponse: Guide details.
    """
    guide = await service.get_guide_with_owner_check(guide_id, current_account.id)
    return LifestyleGuideResponse.model_validate(guide)


@router.delete(
    "/{guide_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lifestyle guide",
)
async def delete_guide(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> None:
    """Delete a lifestyle guide and handle its associated challenges.

    Unstarted challenges are soft-deleted. Active or completed challenges
    are preserved with guide_id set to None.

    Args:
        guide_id: Guide UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.
    """
    await service.delete_guide_with_owner_check(guide_id, current_account.id)


@router.get(
    "/{guide_id}/challenges",
    response_model=list[ChallengeResponse],
    summary="List guide challenges",
)
async def get_guide_challenges(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> list[ChallengeResponse]:
    """Get all challenges generated from a specific lifestyle guide.

    Args:
        guide_id: Guide UUID.
        current_account: Current authenticated account.
        service: Lifestyle guide service instance.

    Returns:
        list[ChallengeResponse]: Challenges linked to the guide.
    """
    challenges = await service.get_guide_challenges_with_owner_check(guide_id, current_account.id)
    return [ChallengeResponse.model_validate(c) for c in challenges]
