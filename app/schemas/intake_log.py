from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseIntakeLog(BaseModel):
    scheduled_date: date = Field(..., description="복용 예정 날짜")
    scheduled_time: time = Field(..., description="복용 예정 시간")
    intake_status: str = Field("SCHEDULED", max_length=16, description="복용 상태 (예: SCHEDULED, TAKEN, MISSED)")
    taken_at: Optional[datetime] = Field(None, description="실제 복용 완료 시간")


class IntakeLogCreate(BaseIntakeLog):
    medication_id: UUID = Field(..., description="연결된 약품 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")


class IntakeLogUpdate(BaseModel):
    scheduled_date: Optional[date] = Field(None, description="복용 예정 날짜")
    scheduled_time: Optional[time] = Field(None, description="복용 예정 시간")
    intake_status: Optional[str] = Field(None, max_length=16, description="복용 상태")
    taken_at: Optional[datetime] = Field(None, description="실제 복용 완료 시간")


class IntakeLogResponse(BaseIntakeLog):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="복약 기록 레코드 ID")
    medication_id: UUID = Field(..., description="연결된 약품 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
