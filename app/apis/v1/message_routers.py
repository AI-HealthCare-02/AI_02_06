"""
Message Router

채팅 메시지 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dtos.message import MessageCreate, MessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Chat"])


def get_message_service() -> MessageService:
    return MessageService()


MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송",
)
async def send_message(
    data: MessageCreate,
    service: MessageServiceDep,
):
    """채팅 세션 내에서 메시지를 전송합니다."""
    message = await service.create_user_message(
        session_id=data.session_id,
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
    service: MessageServiceDep,
    limit: int | None = None,
):
    """특정 채팅 세션의 모든 메시지 이력을 시간순으로 조회합니다."""
    messages = await service.get_messages_by_session(session_id, limit)
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="메시지 삭제",
)
async def delete_message(
    message_id: UUID,
    service: MessageServiceDep,
):
    """특정 메시지를 삭제합니다."""
    await service.delete_message(message_id)
    return None
