"""Intake log DTO models module.

This module contains data transfer objects for medication intake log operations
including creation, updates, and response serialization.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
