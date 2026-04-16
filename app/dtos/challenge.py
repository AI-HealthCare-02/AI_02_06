from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChallengeCreate(BaseModel):
    """챌린지 생성 요청"""

    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    title: str = Field(..., max_length=64, description="챌린지 제목")
    description: str | None = Field(None, max_length=256, description="상세 설명")
    target_days: int = Field(..., description="목표 달성 일수")
    difficulty: str | None = Field(None, max_length=16, description="난이도 (쉬움/보통/어려움)")
    started_date: date | None = Field(None, description="챌린지 시작 날짜 (미입력 시 오늘)")


class ChallengeUpdate(BaseModel):
    title: str | None = Field(None, max_length=64, description="챌린지 제목")
    description: str | None = Field(None, max_length=256, description="상세 설명")
    target_days: int | None = Field(None, description="목표 달성 일수")
    difficulty: str | None = Field(None, max_length=16, description="난이도 (쉬움/보통/어려움)")
    completed_dates: list[date] | None = Field(None, description="달성 완료 날짜 목록")
    challenge_status: str | None = Field(None, max_length=16, description="진행 상태")
    started_date: date | None = Field(None, description="챌린지 시작 날짜")


class ChallengeResponse(BaseModel):
    """챌린지 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="챌린지 레코드 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    title: str = Field(..., description="챌린지 제목")
    description: str | None = Field(None, description="상세 설명")
    target_days: int = Field(..., description="목표 달성 일수")
    difficulty: str | None = Field(None, description="난이도 (쉬움/보통/어려움)")
    completed_dates: list[date] = Field(default_factory=list, description="달성 완료 날짜 목록")
    challenge_status: str = Field(..., description="진행 상태")
    started_date: date = Field(..., description="챌린지 시작 날짜")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    deleted_at: datetime | None = Field(None, description="삭제 일시")
