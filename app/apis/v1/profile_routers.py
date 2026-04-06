from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dtos.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.models.profiles import Profile

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED, summary="프로필 생성")
async def create_profile(data: ProfileCreate):
    """
    새로운 사용자 프로필을 생성합니다.
    """
    new_profile = await Profile.create(**data.model_dump())
    return ProfileResponse.model_validate(new_profile)


@router.get("/{profile_id}", response_model=ProfileResponse, summary="프로필 상세 조회")
async def get_profile(profile_id: UUID):
    """
    특정 프로필의 상세 정보를 조회합니다.
    """
    profile = await Profile.get_or_none(id=profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필을 찾을 수 없습니다.")
    return ProfileResponse.model_validate(profile)


@router.get("/", response_model=list[ProfileResponse], summary="프로필 목록 조회")
async def list_profiles(account_id: UUID | None = None):
    """
    모든 프로필 목록을 조회합니다. 특정 계정(account_id)으로 필터링이 가능합니다.
    """
    query = Profile.all()
    if account_id:
        query = query.filter(account_id=account_id)
    profiles = await query
    return [ProfileResponse.model_validate(p) for p in profiles]


@router.patch("/{profile_id}", response_model=ProfileResponse, summary="프로필 수정")
async def update_profile(profile_id: UUID, data: ProfileUpdate):
    """
    프로필 정보를 수정합니다.
    """
    profile = await Profile.get_or_none(id=profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필을 찾을 수 없습니다.")

    update_data = data.model_dump(exclude_unset=True)
    await profile.update_from_dict(update_data).save()
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, summary="프로필 삭제")
async def delete_profile(profile_id: UUID):
    """
    프로필을 삭제합니다.
    """
    profile = await Profile.get_or_none(id=profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필을 찾을 수 없습니다.")

    await profile.delete()
    return
