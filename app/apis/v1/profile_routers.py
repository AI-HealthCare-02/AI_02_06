"""
Profile Router

프로필 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.models.accounts import Account
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_profile_service() -> ProfileService:
    return ProfileService()


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="프로필 생성",
)
async def create_profile(
    data: ProfileCreate,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
):
    """새로운 사용자 프로필을 생성합니다."""
    # 인증된 계정 ID를 사용 (요청 body의 account_id 무시)
    profile = await service.create_profile(current_account.id, data)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="프로필 상세 조회",
)
async def get_profile(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
):
    """특정 프로필의 상세 정보를 조회합니다."""
    profile = await service.get_profile_with_owner_check(profile_id, current_account.id)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/",
    response_model=list[ProfileResponse],
    summary="프로필 목록 조회",
)
async def list_profiles(
    current_account: CurrentAccount,
    service: ProfileServiceDep,
):
    """현재 계정의 모든 프로필 목록을 조회합니다."""
    profiles = await service.get_profiles_by_account(current_account.id)
    return [ProfileResponse.model_validate(p) for p in profiles]


@router.patch(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="프로필 수정",
)
async def update_profile(
    profile_id: UUID,
    data: ProfileUpdate,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
):
    """프로필 정보를 수정합니다."""
    profile = await service.update_profile_with_owner_check(profile_id, current_account.id, data)
    return ProfileResponse.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="프로필 삭제",
)
async def delete_profile(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: ProfileServiceDep,
):
    """프로필을 삭제합니다."""
    await service.delete_profile_with_owner_check(profile_id, current_account.id)
    return None
