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

    medicine_name: str = Field(..., max_length=128, description="Medicine name")
    dose_per_intake: str | None = Field(None, max_length=32, description="Dose per intake (e.g., 1 tablet, 5ml)")
    intake_instruction: str | None = Field(None, max_length=256, description="Intake instructions")
    intake_times: list[str] = Field(..., description="Daily intake times list (e.g., ['08:00', '13:00'])")
    total_intake_count: int = Field(..., description="Total prescribed intake count")
    remaining_intake_count: int | None = Field(
        None,
        description="Remaining intake count (defaults to total intake count if not provided)",
    )
    start_date: date = Field(..., description="Intake start date")
    end_date: date | None = Field(None, description="Expected intake end date")
    dispensed_date: date | None = Field(None, description="Medicine dispensing date")
    expiration_date: date | None = Field(None, description="Medicine expiration date")
    prescription_image_url: str | None = Field(None, max_length=512, description="Prescription image URL")
    is_active: bool = Field(True, description="Currently taking status")


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

    medicine_name: str | None = Field(None, max_length=128, description="Medicine name")
    dose_per_intake: str | None = Field(None, max_length=32, description="Dose per intake")
    intake_instruction: str | None = Field(None, max_length=256, description="Intake instructions")
    intake_times: list[str] | None = Field(None, description="Daily intake times list")
    total_intake_count: int | None = Field(None, description="Total prescribed intake count")
    remaining_intake_count: int | None = Field(None, description="Remaining intake count")
    start_date: date | None = Field(None, description="Intake start date")
    end_date: date | None = Field(None, description="Expected intake end date")
    dispensed_date: date | None = Field(None, description="Medicine dispensing date")
    expiration_date: date | None = Field(None, description="Medicine expiration date")
    prescription_image_url: str | None = Field(None, max_length=512, description="Prescription image URL")
    is_active: bool | None = Field(None, description="Currently taking status")


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
