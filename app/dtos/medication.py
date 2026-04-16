"""Medication DTO models module.

This module contains data transfer objects for medication operations
including creation, updates, and response serialization.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseMedication(BaseModel):
    """Base medication model with common fields.

    Provides shared fields for medication operations
    including dosage, schedule, and prescription information.
    """

    medicine_name: str = Field(..., max_length=128, description="약품명")
    department: str | None = Field(None, max_length=64, description="처방 진료과 (예: 내과)")
    category: str | None = Field(None, max_length=64, description="약품 분류 (예: 해열진통제)")
    dose_per_intake: str | None = Field(None, max_length=32, description="1회 복용량 (예: 1정, 5ml)")
    daily_intake_count: int | None = Field(None, description="1일 복용 횟수")
    total_intake_days: int | None = Field(None, description="총 복용 일수")
    intake_instruction: str | None = Field(None, max_length=256, description="복용 지시사항")
    intake_times: list[str] = Field(..., description="일일 복용 시간 목록 (예: ['08:00', '13:00'])")
    total_intake_count: int = Field(..., description="처방된 총 복용 횟수")
    remaining_intake_count: int | None = Field(None, description="남은 복용 횟수 (미입력 시 총 복용 횟수와 동일)")
    start_date: date = Field(..., description="복용 시작일")
    end_date: date | None = Field(None, description="복용 종료 예정일")
    dispensed_date: date | None = Field(None, description="약품 조제일")
    expiration_date: date | None = Field(None, description="약품 유효기간 만료일")
    prescription_image_url: str | None = Field(None, max_length=512, description="처방전 이미지 URL")
    is_active: bool = Field(True, description="현재 복용 중 여부")


class MedicationCreate(BaseMedication):
    """Medication creation request model.

    Used for creating new medications with profile association.
    """

    profile_id: UUID = Field(..., description="Connected profile ID")


class MedicationUpdate(BaseModel):
    """Medication update request model.

    Used for partial updates to existing medications.
    All fields are optional for flexible updates.
    """

    medicine_name: str | None = Field(None, max_length=128, description="약품명")
    department: str | None = Field(None, max_length=64, description="처방 진료과")
    category: str | None = Field(None, max_length=64, description="약품 분류")
    dose_per_intake: str | None = Field(None, max_length=32, description="1회 복용량")
    daily_intake_count: int | None = Field(None, description="1일 복용 횟수")
    total_intake_days: int | None = Field(None, description="총 복용 일수")
    intake_instruction: str | None = Field(None, max_length=256, description="복용 지시사항")
    intake_times: list[str] | None = Field(None, description="일일 복용 시간 목록")
    total_intake_count: int | None = Field(None, description="처방된 총 복용 횟수")
    remaining_intake_count: int | None = Field(None, description="남은 복용 횟수")
    start_date: date | None = Field(None, description="복용 시작일")
    end_date: date | None = Field(None, description="복용 종료 예정일")
    dispensed_date: date | None = Field(None, description="약품 조제일")
    expiration_date: date | None = Field(None, description="약품 유효기간 만료일")
    prescription_image_url: str | None = Field(None, max_length=512, description="처방전 이미지 URL")
    is_active: bool | None = Field(None, description="현재 복용 중 여부")


class MedicationResponse(BaseMedication):
    """Medication response model.

    Used for serializing medication data in API responses.
    Includes all medication fields and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Medication record ID")
    profile_id: UUID = Field(..., description="Connected profile ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")
