"""Message API router module.

This module contains HTTP endpoints for chat message operations
including sending messages, retrieving chat history, and AI responses.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.message import (
    ChatAskRequest,
    ChatAskResponse,
    MessageCreate,
    MessageResponse,
)
from app.models.accounts import Account
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Chat"])


def get_message_service() -> MessageService:
    """Get message service instance.

    Returns:
        MessageService: Message service instance.
    """
    return MessageService()


# Type aliases for dependency injection
MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send user question and receive AI response",
)
async def ask_message(
    data: ChatAskRequest,
    service: MessageServiceDep,
) -> ChatAskResponse:
    """Send user message and generate RAG-based AI response.

    Args:
        data: Chat ask request data containing session ID and message content.
        service: Message service instance.

    Returns:
        ChatAskResponse: Response containing both user and assistant messages.
    """
    user_msg, assistant_msg = await service.ask_and_reply(
        session_id=data.session_id,
        content=data.content,
    )
    return ChatAskResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
)
async def send_message(
    data: MessageCreate,
    current_account: CurrentAccount,
    service: MessageServiceDep,
) -> MessageResponse:
    """Send a message within a chat session.

    Args:
        data: Message creation data.
        current_account: Current authenticated account.
        service: Message service instance.

    Returns:
        MessageResponse: Created message information.
    """
    message = await service.create_user_message_with_owner_check(
        session_id=data.session_id,
        account_id=current_account.id,
        content=data.content,
    )
    return MessageResponse.model_validate(message)


@router.get(
    "/session/{session_id}",
    response_model=list[MessageResponse],
    summary="Get chat history",
)
async def list_messages(
    session_id: UUID,
    current_account: CurrentAccount,
    service: MessageServiceDep,
    limit: int | None = None,
) -> list[MessageResponse]:
    """Get all message history for a specific chat session in chronological order.

    Args:
        session_id: Chat session ID to retrieve messages from.
        current_account: Current authenticated account.
        service: Message service instance.
        limit: Optional limit on number of messages to retrieve.

    Returns:
        List[MessageResponse]: List of messages in chronological order.
    """
    messages = await service.get_messages_by_session_with_owner_check(session_id, current_account.id, limit)
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete message",
)
async def delete_message(
    message_id: UUID,
    current_account: CurrentAccount,
    service: MessageServiceDep,
) -> None:
    """Delete a specific message.

    Args:
        message_id: Message ID to delete.
        current_account: Current authenticated account.
        service: Message service instance.
    """
    await service.delete_message_with_owner_check(message_id, current_account.id)
