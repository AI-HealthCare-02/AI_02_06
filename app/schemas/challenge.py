from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseChallenge(BaseModel):
    title: str = Field(..., max_length=64, description="챌린지 제목")
    description: Optional[str] = Field(None, max_length=256, description="상세 설명")
    target_days: int = Field(..., description="목표 달성 일수")
    completed_dates: List[date] = Field(default_factory=list, description="달성 완료 날짜 목록")
    challenge_status: str = Field("IN_PROGRESS", max_length=16, description="진행 상태")
    started_date: date = Field(..., description="챌린지 시작 날짜")


class ChallengeCreate(BaseChallenge):
    profile_id: UUID = Field(..., description="연결된 프로필 ID")


class ChallengeUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=64, description="챌린지 제목")
    description: Optional[str] = Field(None, max_length=256, description="상세 설명")
    target_days: Optional[int] = Field(None, description="목표 달성 일수")
    completed_dates: Optional[List[date]] = Field(None, description="달성 완료 날짜 목록")
    challenge_status: Optional[str] = Field(None, max_length=16, description="진행 상태")
    started_date: Optional[date] = Field(None, description="챌린지 시작 날짜")


class ChallengeResponse(BaseChallenge):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="챌린지 레코드 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    deleted_at: Optional[datetime] = Field(None, description="삭제 일시")
