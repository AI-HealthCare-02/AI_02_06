from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseMedication(BaseModel):
    medicine_name: str = Field(..., max_length=128, description="약품명")
    dose_per_intake: Optional[str] = Field(None, max_length=32, description="1회 복용량 (예: 1정, 5ml)")
    intake_instruction: Optional[str] = Field(None, max_length=256, description="복용 지시사항")
    intake_times: List[str] = Field(..., description="일일 복용 시간 목록 (예: ['08:00', '13:00'])")
    total_intake_count: int = Field(..., description="처방된 총 복용 횟수")
    remaining_intake_count: int = Field(..., description="남은 복용 횟수")
    start_date: date = Field(..., description="복용 시작일")
    end_date: Optional[date] = Field(None, description="복용 종료 예정일")
    dispensed_date: Optional[date] = Field(None, description="약품 조제일")
    expiration_date: Optional[date] = Field(None, description="약품 유효기간 만료일")
    prescription_image_url: Optional[str] = Field(None, max_length=512, description="처방전 이미지 URL")
    is_active: bool = Field(True, description="현재 복용 중 여부")


class MedicationCreate(BaseMedication):
    profile_id: UUID = Field(..., description="연결된 프로필 ID")


class MedicationUpdate(BaseModel):
    medicine_name: Optional[str] = Field(None, max_length=128, description="약품명")
    dose_per_intake: Optional[str] = Field(None, max_length=32, description="1회 복용량")
    intake_instruction: Optional[str] = Field(None, max_length=256, description="복용 지시사항")
    intake_times: Optional[List[str]] = Field(None, description="일일 복용 시간 목록")
    total_intake_count: Optional[int] = Field(None, description="처방된 총 복용 횟수")
    remaining_intake_count: Optional[int] = Field(None, description="남은 복용 횟수")
    start_date: Optional[date] = Field(None, description="복용 시작일")
    end_date: Optional[date] = Field(None, description="복용 종료 예정일")
    dispensed_date: Optional[date] = Field(None, description="약품 조제일")
    expiration_date: Optional[date] = Field(None, description="약품 유효기간 만료일")
    prescription_image_url: Optional[str] = Field(None, max_length=512, description="처방전 이미지 URL")
    is_active: Optional[bool] = Field(None, description="현재 복용 중 여부")


class MedicationResponse(BaseMedication):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="약품 레코드 ID")
    profile_id: UUID = Field(..., description="연결된 프로필 ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    deleted_at: Optional[datetime] = Field(None, description="삭제 일시")
