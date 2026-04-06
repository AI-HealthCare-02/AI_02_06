from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationType(StrEnum):
    SELF = "SELF"
    PARENT = "PARENT"
    CHILD = "CHILD"
    SPOUSE = "SPOUSE"
    OTHER = "OTHER"


class BaseProfile(BaseModel):
    relation_type: RelationType = Field(..., description="관계 유형 (SELF, PARENT, CHILD, SPOUSE, OTHER)")
    name: str = Field(..., max_length=32, description="프로필 이름")
    health_survey: dict[str, Any] | None = Field(default=None, description="건강 설문 결과 (JSON)")


class ProfileCreate(BaseProfile):
    account_id: UUID = Field(..., description="연결된 계정 ID")


class ProfileUpdate(BaseModel):
    relation_type: RelationType | None = Field(None, description="관계 유형")
    name: str | None = Field(None, max_length=32, description="프로필 이름")
    health_survey: dict[str, Any] | None = Field(None, description="건강 설문 결과")


class ProfileResponse(BaseProfile):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="프로필 고유 ID")
    account_id: UUID = Field(..., description="연결된 계정 ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    deleted_at: datetime | None = Field(None, description="삭제 일시")
