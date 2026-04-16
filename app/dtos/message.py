"""Message DTO models module.

This module contains data transfer objects for chat message operations
including creation, AI chat requests, and response serialization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.messages import SenderType


class MessageCreate(BaseModel):
    """Message creation request model.

    Used for creating new messages within chat sessions
    with sender type specification.
    """

    session_id: UUID = Field(..., description="Connected chat session ID")
    sender_type: SenderType = Field(..., description="Sender type (USER, ASSISTANT)")
    content: str = Field(..., description="Message content")


class ChatAskRequest(BaseModel):
    """Chat ask request model.

    Used for user questions that trigger AI responses
    in the RAG-based chat system.
    """

    session_id: UUID = Field(..., description="Connected chat session ID")
    content: str = Field(..., description="User question")


class MessageResponse(BaseModel):
    """Message response model.

    Used for serializing message data in API responses.
    Includes all message fields and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Message unique ID")
    session_id: UUID = Field(..., description="Connected session ID")
    sender_type: SenderType = Field(..., description="Sender type")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Send timestamp")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")


class ChatAskResponse(BaseModel):
    """Chat ask response model.

    Used for returning both user and AI assistant messages
    in a single response after AI processing.
    """

    user_message: MessageResponse
    assistant_message: MessageResponse
