"""Profile API router module.

This module contains HTTP endpoints for user profile operations
including creating, reading, updating, and deleting profiles.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.profile import ProfileCreate, ProfileResponse, ProfileSummaryResponse, ProfileUpdate
from app.models.accounts import Account
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_profile_service() -> ProfileService:
    """Get profile service instance.

    Returns:
        ProfileService: Profile service instance.
    """
    return ProfileService()


# Type aliases for dependency injection
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create profile",
)
async def create_profile(
    data: ProfileCreate,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """Create a new user profile.

    Args:
        data: Profile creation data.
        current_account: Current authenticated account.
        service: Profile service instance.

    Returns:
        ProfileResponse: Created profile information.
    """
    # Use authenticated account ID (ignore account_id from request body)
    profile = await service.create_profile(current_account.id, data)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="Get profile details",
)
async def get_profile(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """Get detailed information about a specific profile.

    Args:
        profile_id: Profile ID to retrieve.
        current_account: Current authenticated account.
        service: Profile service instance.

    Returns:
        ProfileResponse: Profile details.
    """
    profile = await service.get_profile_with_owner_check(profile_id, current_account.id)
    return ProfileResponse.model_validate(profile)


@router.get(
    "",
    response_model=list[ProfileSummaryResponse],
    summary="List profiles",
)
async def list_profiles(
    current_account: CurrentAccount,
    service: ProfileServiceDep,
) -> list[ProfileSummaryResponse]:
    """Get all profile list for the current account.

    Returns lightweight summary (no health_survey) for profile switching UI.
    Use GET /profiles/{id} to retrieve full profile including health survey data.

    Args:
        current_account: Current authenticated account.
        service: Profile service instance.

    Returns:
        List[ProfileSummaryResponse]: Summary list of profiles for the account.
    """
    # ProfileSummaryResponse(경량 요약 DTO)를 제거하고 ProfileResponse로 통일.
    # 프론트엔드에서 프로필 전환 UI(ProfileSwitcher 컴포넌트, ProfileContext)를 삭제하면서
    # 경량 DTO를 별도로 유지할 필요가 없어졌기 때문.
    profiles = await service.get_profiles_by_account(current_account.id)
    return [ProfileSummaryResponse.model_validate(p) for p in profiles]


@router.patch(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="Update profile",
)
async def update_profile(
    profile_id: UUID,
    data: ProfileUpdate,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """Update profile information.

    Args:
        profile_id: Profile ID to update.
        data: Profile update data.
        current_account: Current authenticated account.
        service: Profile service instance.

    Returns:
        ProfileResponse: Updated profile information.
    """
    profile = await service.update_profile_with_owner_check(profile_id, current_account.id, data)
    return ProfileResponse.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete profile",
)
async def delete_profile(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
) -> None:
    """Delete a profile.

    Args:
        profile_id: Profile ID to delete.
        current_account: Current authenticated account.
        service: Profile service instance.
    """
    await service.delete_profile_with_owner_check(profile_id, current_account.id)
