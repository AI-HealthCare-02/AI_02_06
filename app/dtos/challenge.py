"""Challenge DTO models module.

This module contains data transfer objects for challenge-related operations
including creation, updates, and response serialization.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChallengeCreate(BaseModel):
    """Challenge creation request model.

    Used for creating new challenges with required fields
    and optional configuration.
    """

    profile_id: UUID = Field(..., description="Connected profile ID")
    title: str = Field(..., max_length=64, description="Challenge title")
    description: str | None = Field(None, max_length=256, description="Detailed description")
    target_days: int = Field(..., description="Target achievement days")
    started_date: date | None = Field(None, description="Challenge start date (defaults to today if not provided)")


class ChallengeUpdate(BaseModel):
    """Challenge update request model.

    Used for partial updates to existing challenges.
    All fields are optional for flexible updates.
    """

    title: str | None = Field(None, max_length=64, description="Challenge title")
    description: str | None = Field(None, max_length=256, description="Detailed description")
    target_days: int | None = Field(None, description="Target achievement days")
    completed_dates: list[date] | None = Field(None, description="List of completion dates")
    challenge_status: str | None = Field(None, max_length=16, description="Progress status")
    started_date: date | None = Field(None, description="Challenge start date")


class ChallengeResponse(BaseModel):
    """Challenge response model.

    Used for serializing challenge data in API responses.
    Includes all challenge fields and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Challenge record ID")
    profile_id: UUID = Field(..., description="Connected profile ID")
    title: str = Field(..., description="Challenge title")
    description: str | None = Field(None, description="Detailed description")
    target_days: int = Field(..., description="Target achievement days")
    completed_dates: list[date] = Field(default_factory=list, description="List of completion dates")
    challenge_status: str = Field(..., description="Progress status")
    started_date: date = Field(..., description="Challenge start date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")
