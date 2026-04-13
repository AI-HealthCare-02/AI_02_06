from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    account_id: UUID | None = Field(None, description="연결된 계정 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    medication_id: UUID | None = Field(None, description="특정 약품 관련 상담 시 약품 ID")
    title: str | None = Field(None, max_length=64, description="세션 제목")


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="세션 고유 ID")
    account_id: UUID = Field(..., description="연결된 계정 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    medication_id: UUID | None = Field(None, description="연결된 약품 ID")
    title: str | None = Field(None, description="세션 제목")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    deleted_at: datetime | None = Field(None, description="삭제 일시")
