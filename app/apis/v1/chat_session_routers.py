"""
ChatSession Router

채팅 세션 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.chat_session import ChatSessionCreate, ChatSessionResponse
from app.models.accounts import Account
from app.services.chat_session_service import ChatSessionService

router = APIRouter(prefix="/chat-sessions", tags=["Chat"])


def get_chat_session_service() -> ChatSessionService:
    return ChatSessionService()


ChatSessionServiceDep = Annotated[ChatSessionService, Depends(get_chat_session_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채팅 세션 생성",
)
async def create_chat_session(
    data: ChatSessionCreate,
    current_account: CurrentAccount,
    service: ChatSessionServiceDep,
):
    """새로운 채팅 상담 세션을 시작합니다."""
    # 인증된 계정 ID를 사용 (요청 body의 account_id 무시)
    session = await service.create_session_with_owner_check(
        account_id=current_account.id,
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
    current_account: CurrentAccount,
    service: ChatSessionServiceDep,
):
    """특정 채팅 세션의 상세 정보를 조회합니다."""
    session = await service.get_session_with_owner_check(session_id, current_account.id)
    return ChatSessionResponse.model_validate(session)


@router.get(
    "",
    response_model=list[ChatSessionResponse],
    summary="채팅 세션 목록 조회",
)
async def list_chat_sessions(
    current_account: CurrentAccount,
    service: ChatSessionServiceDep,
    profile_id: UUID | None = None,
):
    """채팅 세션 목록을 조회합니다. 프로필 ID로 필터링할 수 있습니다."""
    if profile_id:
        sessions = await service.get_sessions_by_profile_with_owner_check(profile_id, current_account.id)
    else:
        sessions = await service.get_sessions_by_account(current_account.id)
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="채팅 세션 삭제",
)
async def delete_chat_session(
    session_id: UUID,
    current_account: CurrentAccount,
    service: ChatSessionServiceDep,
):
    """채팅 세션을 삭제합니다."""
    await service.delete_session_with_owner_check(session_id, current_account.id)
    return None
