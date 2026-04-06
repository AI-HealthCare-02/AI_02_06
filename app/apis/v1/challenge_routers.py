from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dtos.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.models.challenge import Challenge

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
    challenge = await Challenge.get_or_none(id=challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    return ChallengeResponse.model_validate(challenge)


@router.patch("/{challenge_id}", response_model=ChallengeResponse)
async def update_challenge(challenge_id: UUID, data: ChallengeUpdate):
    challenge = await Challenge.get_or_none(id=challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(challenge, key, value)
    await challenge.save()
    return ChallengeResponse.model_validate(challenge)


@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(challenge_id: UUID):
    challenge = await Challenge.get_or_none(id=challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    await challenge.delete()
    return None
