"""Chat session DTO models module.

This module contains data transfer objects for chat session operations
including creation and response serialization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    """Chat session creation request model.

    Used for creating new chat sessions with optional
    medication-specific consultation context.
    """

    profile_id: UUID = Field(..., description="Connected profile ID")
    medication_id: UUID | None = Field(None, description="Specific medication ID for medication-related consultation")
    title: str | None = Field(None, max_length=64, description="Session title")


class ChatSessionResponse(BaseModel):
    """Chat session response model.

    Used for serializing chat session data in API responses.
    Includes all session fields and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Session unique ID")
    account_id: UUID = Field(..., description="Connected account ID")
    profile_id: UUID = Field(..., description="Connected profile ID")
    medication_id: UUID | None = Field(None, description="Connected medication ID")
    title: str | None = Field(None, description="Session title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")
