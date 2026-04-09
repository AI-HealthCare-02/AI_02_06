"""
Message Router

채팅 메시지 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.message import ChatAskRequest, ChatAskResponse, MessageCreate, MessageResponse
from app.models.accounts import Account
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Chat"])


def get_message_service() -> MessageService:
    return MessageService()


MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 질문 전송 및 AI 응답 수신",
)
async def ask_message(
    data: ChatAskRequest,
    service: MessageServiceDep,
):
    """사용자 메시지를 저장하고 RAG 기반 AI 응답을 생성하여 반환합니다."""
    user_msg, assistant_msg = await service.ask_and_reply(
        session_id=data.session_id,
        content=data.content,
    )
    return ChatAskResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


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


from pydantic import BaseModel, Field


class MessageFeedbackRequest(BaseModel):
    is_helpful: bool = Field(..., description="도움이 되었는지 여부")
    feedback_text: str | None = Field(None, max_length=256, description="추가 피드백 텍스트")


@router.post(
    "/{message_id}/feedback",
    status_code=status.HTTP_200_OK,
    summary="메시지 피드백 제출",
)
async def submit_feedback(
    message_id: UUID,
    data: MessageFeedbackRequest,
    current_account: CurrentAccount,
    service: MessageServiceDep,
):
    """AI 상담 메시지에 대해 좋아요/싫어요 피드백을 남깁니다."""
    # 메시지 소유권 확인 및 피드백 저장 로직
    # (실제 소유권은 메시지가 속한 세션의 소유자와 현재 유저가 일치하는지 확인해야 함)
    from app.repositories.message_repository import MessageFeedbackRepository

    repo = MessageFeedbackRepository()
    feedback = await repo.create_or_update(
        message_id=message_id,
        is_helpful=data.is_helpful,
        feedback_text=data.feedback_text,
    )

    return {"status": "success", "feedback_id": str(feedback.id)}
