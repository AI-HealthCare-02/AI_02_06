from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dtos.chat_session import ChatSessionCreate, ChatSessionResponse
from app.models.chat_sessions import ChatSession

router = APIRouter(prefix="/chat-sessions", tags=["Chat"])


@router.post("/", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED, summary="채팅 세션 생성")
async def create_chat_session(data: ChatSessionCreate):
    """
    새로운 채팅 상담 세션을 시작합니다.
    """
    new_session = await ChatSession.create(**data.model_dump())
    return ChatSessionResponse.model_validate(new_session)


@router.get("/{session_id}", response_model=ChatSessionResponse, summary="채팅 세션 상세 조회")
async def get_chat_session(session_id: UUID):
    """
    특정 채팅 세션의 상세 정보를 조회합니다.
    """
    session = await ChatSession.get_or_none(id=session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")
    return ChatSessionResponse.model_validate(session)


@router.get("/", response_model=list[ChatSessionResponse], summary="채팅 세션 목록 조회")
async def list_chat_sessions(account_id: UUID | None = None, profile_id: UUID | None = None):
    """
    채팅 세션 목록을 조회합니다. 계정 또는 프로필 ID로 필터링할 수 있습니다.
    """
    query = ChatSession.all().order_by("-created_at")
    if account_id:
        query = query.filter(account_id=account_id)
    if profile_id:
        query = query.filter(profile_id=profile_id)
    
    sessions = await query
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="채팅 세션 삭제")
async def delete_chat_session(session_id: UUID):
    """
    채팅 세션을 삭제합니다.
    """
    session = await ChatSession.get_or_none(id=session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")
    
    await session.delete()
    return
