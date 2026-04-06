from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.messages import SenderType


class MessageCreate(BaseModel):
    session_id: UUID = Field(..., description="연결된 채팅 세션 ID")
    sender_type: SenderType = Field(..., description="전송자 타입 (USER, ASSISTANT)")
    content: str = Field(..., description="메시지 내용")


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="메시지 고유 ID")
    session_id: UUID = Field(..., description="연결된 세션 ID")
    sender_type: SenderType = Field(..., description="전송자 타입")
    content: str = Field(..., description="메시지 내용")
    created_at: datetime = Field(..., description="전송 일시")
    deleted_at: datetime | None = Field(None, description="삭제 일시")
