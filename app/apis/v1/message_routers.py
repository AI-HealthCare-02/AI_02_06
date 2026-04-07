"""
Message Router

채팅 메시지 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.message import MessageCreate, MessageResponse
from app.models.accounts import Account
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Chat"])


def get_message_service() -> MessageService:
    return MessageService()


MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송",
)
async def send_message(
    data: MessageCreate,
    current_account: CurrentAccount,
    service: MessageServiceDep,
):
    """채팅 세션 내에서 메시지를 전송합니다."""
    message = await service.create_user_message_with_owner_check(
        session_id=data.session_id,
        account_id=current_account.id,
        content=data.content,
    )
    return MessageResponse.model_validate(message)


@router.get(
    "/session/{session_id}",
    response_model=list[MessageResponse],
    summary="채팅 이력 조회",
)
async def list_messages(
    session_id: UUID,
    current_account: CurrentAccount,
    service: MessageServiceDep,
    limit: int | None = None,
):
    """특정 채팅 세션의 모든 메시지 이력을 시간순으로 조회합니다."""
    messages = await service.get_messages_by_session_with_owner_check(session_id, current_account.id, limit)
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="메시지 삭제",
)
async def delete_message(
    message_id: UUID,
    current_account: CurrentAccount,
    service: MessageServiceDep,
):
    """특정 메시지를 삭제합니다."""
    await service.delete_message_with_owner_check(message_id, current_account.id)
    return None
