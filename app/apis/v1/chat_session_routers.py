"""
ChatSession Router

채팅 세션 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dtos.chat_session import ChatSessionCreate, ChatSessionResponse
from app.services.chat_session_service import ChatSessionService

router = APIRouter(prefix="/chat-sessions", tags=["Chat"])


def get_chat_session_service() -> ChatSessionService:
    return ChatSessionService()


ChatSessionServiceDep = Annotated[ChatSessionService, Depends(get_chat_session_service)]


@router.post(
    "/",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채팅 세션 생성",
)
async def create_chat_session(
    data: ChatSessionCreate,
    service: ChatSessionServiceDep,
):
    """새로운 채팅 상담 세션을 시작합니다."""
    session = await service.create_session(
        account_id=data.account_id,
        profile_id=data.profile_id,
        medication_id=data.medication_id,
        title=data.title,
    )
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/{session_id}",
    response_model=ChatSessionResponse,
    summary="채팅 세션 상세 조회",
)
async def get_chat_session(
    session_id: UUID,
    service: ChatSessionServiceDep,
):
    """특정 채팅 세션의 상세 정보를 조회합니다."""
    session = await service.get_session(session_id)
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/",
    response_model=list[ChatSessionResponse],
    summary="채팅 세션 목록 조회",
)
async def list_chat_sessions(
    service: ChatSessionServiceDep,
    account_id: UUID | None = None,
    profile_id: UUID | None = None,
):
    """채팅 세션 목록을 조회합니다. 계정 또는 프로필 ID로 필터링할 수 있습니다."""
    if account_id:
        sessions = await service.get_sessions_by_account(account_id)
    elif profile_id:
        sessions = await service.get_sessions_by_profile(profile_id)
    else:
        from app.models.chat_sessions import ChatSession

        sessions = await ChatSession.filter(deleted_at__isnull=True).order_by("-created_at").all()
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="채팅 세션 삭제",
)
async def delete_chat_session(
    session_id: UUID,
    service: ChatSessionServiceDep,
):
    """채팅 세션을 삭제합니다."""
    await service.delete_session(session_id)
    return None
