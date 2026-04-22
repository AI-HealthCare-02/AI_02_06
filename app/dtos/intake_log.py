"""Intake log DTO models module.

This module contains data transfer objects for medication intake log operations
including creation, updates, and response serialization.
"""

import zoneinfo
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# DTO 경계에서 naive datetime 유입을 차단하기 위한 KST 타임존 상수
_KST = zoneinfo.ZoneInfo("Asia/Seoul")


def _make_aware(v: datetime | None) -> datetime | None:
    """Return timezone-aware datetime; assume KST if tzinfo is missing.

    tzinfo가 없는 naive datetime은 KST로 간주하여 aware datetime으로 변환합니다.
    이미 aware datetime이면 그대로 반환합니다.
    """
    if v is None:
        return v
    return v if v.tzinfo is not None else v.replace(tzinfo=_KST)


class BaseIntakeLog(BaseModel):
    """Base intake log model with common fields.

    Provides shared fields for intake log operations
    including scheduling and status information.
    """

    scheduled_date: date = Field(..., description="Scheduled intake date")
    scheduled_time: time = Field(..., description="Scheduled intake time")
    intake_status: str = Field(
        "SCHEDULED",
        max_length=16,
        description="Intake status (e.g., SCHEDULED, TAKEN, MISSED)",
    )
    taken_at: datetime | None = Field(None, description="Actual intake completion time")

    @field_validator("taken_at", mode="before")
    @classmethod
    def ensure_aware_taken_at(cls, v: datetime | None) -> datetime | None:
        """Reject naive datetime; assume KST when tzinfo is absent."""
        return _make_aware(v)


class IntakeLogCreate(BaseIntakeLog):
    """Intake log creation request model.

    Used for creating new medication intake logs
    with medication and profile associations.
    """

    medication_id: UUID = Field(..., description="Connected medication ID")
    profile_id: UUID = Field(..., description="Connected profile ID")


class IntakeLogUpdate(BaseModel):
    """Intake log update request model.

    Used for partial updates to existing intake logs.
    All fields are optional for flexible updates.
    """

    scheduled_date: date | None = Field(None, description="Scheduled intake date")
    scheduled_time: time | None = Field(None, description="Scheduled intake time")
    intake_status: str | None = Field(None, max_length=16, description="Intake status")
    taken_at: datetime | None = Field(None, description="Actual intake completion time")

    @field_validator("taken_at", mode="before")
    @classmethod
    def ensure_aware_taken_at(cls, v: datetime | None) -> datetime | None:
        """Reject naive datetime; assume KST when tzinfo is absent."""
        return _make_aware(v)


class StreakResponse(BaseModel):
    """Medication streak response model.

    Used for returning consecutive medication days count for a profile.
    """

    streak_days: int = Field(..., description="Number of consecutive days with at least one taken medication")


class IntakeLogResponse(BaseIntakeLog):
    """Intake log response model.

    Used for serializing intake log data in API responses.
    Includes all intake log fields and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Intake log record ID")
    medication_id: UUID = Field(..., description="Connected medication ID")
    profile_id: UUID = Field(..., description="Connected profile ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
