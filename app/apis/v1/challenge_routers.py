from uuid import UUID

from fastapi import APIRouter, status

from app.dtos.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.models.challenge import Challenge
from app.utils.common import get_object_or_404

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.post("/", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(data: ChallengeCreate):
    new_challenge = await Challenge.create(**data.model_dump())
    return ChallengeResponse.model_validate(new_challenge)


@router.get("/", response_model=list[ChallengeResponse])
async def list_challenges():
    challenges = await Challenge.all()
    return [ChallengeResponse.model_validate(c) for c in challenges]


@router.get("/{challenge_id}", response_model=ChallengeResponse)
async def get_challenge(challenge_id: UUID):
    challenge = await get_object_or_404(Challenge, id=challenge_id)
    return ChallengeResponse.model_validate(challenge)


@router.patch("/{challenge_id}", response_model=ChallengeResponse)
async def update_challenge(challenge_id: UUID, data: ChallengeUpdate):
    challenge = await get_object_or_404(Challenge, id=challenge_id)

    update_data = data.model_dump(exclude_unset=True)
    await challenge.update_from_dict(update_data).save()
    return ChallengeResponse.model_validate(challenge)


@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(challenge_id: UUID):
    challenge = await get_object_or_404(Challenge, id=challenge_id)
    await challenge.delete()
    return None

