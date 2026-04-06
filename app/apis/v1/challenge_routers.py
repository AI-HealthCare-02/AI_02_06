"""
Challenge Router

챌린지 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dtos.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/challenges", tags=["Challenges"])


def get_challenge_service() -> ChallengeService:
    return ChallengeService()


ChallengeServiceDep = Annotated[ChallengeService, Depends(get_challenge_service)]


@router.post(
    "/",
    response_model=ChallengeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="챌린지 생성",
)
async def create_challenge(
    data: ChallengeCreate,
    service: ChallengeServiceDep,
):
    """새로운 챌린지를 생성합니다."""
    challenge = await service.create_challenge(data.profile_id, data)
    return ChallengeResponse.model_validate(challenge)


@router.get(
    "/",
    response_model=list[ChallengeResponse],
    summary="챌린지 목록 조회",
)
async def list_challenges(
    service: ChallengeServiceDep,
    profile_id: UUID | None = None,
    active_only: bool = False,
):
    """챌린지 목록을 조회합니다. 프로필 ID로 필터링이 가능합니다."""
    if profile_id:
        if active_only:
            challenges = await service.get_active_challenges(profile_id)
        else:
            challenges = await service.get_challenges_by_profile(profile_id)
    else:
        from app.models.challenge import Challenge

        challenges = await Challenge.filter(deleted_at__isnull=True).all()
    return [ChallengeResponse.model_validate(c) for c in challenges]


@router.get(
    "/{challenge_id}",
    response_model=ChallengeResponse,
    summary="챌린지 상세 조회",
)
async def get_challenge(
    challenge_id: UUID,
    service: ChallengeServiceDep,
):
    """특정 챌린지의 상세 정보를 조회합니다."""
    challenge = await service.get_challenge(challenge_id)
    return ChallengeResponse.model_validate(challenge)


@router.patch(
    "/{challenge_id}",
    response_model=ChallengeResponse,
    summary="챌린지 수정",
)
async def update_challenge(
    challenge_id: UUID,
    data: ChallengeUpdate,
    service: ChallengeServiceDep,
):
    """챌린지 정보를 수정합니다."""
    challenge = await service.update_challenge(challenge_id, data)
    return ChallengeResponse.model_validate(challenge)


@router.delete(
    "/{challenge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="챌린지 삭제",
)
async def delete_challenge(
    challenge_id: UUID,
    service: ChallengeServiceDep,
):
    """챌린지를 삭제합니다."""
    await service.delete_challenge(challenge_id)
    return None
