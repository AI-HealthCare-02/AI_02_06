from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dtos.message import MessageCreate, MessageResponse
from app.models.messages import ChatMessage

router = APIRouter(prefix="/messages", tags=["Chat"])


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, summary="메시지 전송")
async def send_message(data: MessageCreate):
    """
    채팅 세션 내에서 메시지를 전송합니다.
    """
    new_message = await ChatMessage.create(**data.model_dump())
    return MessageResponse.model_validate(new_message)


@router.get("/session/{session_id}", response_model=list[MessageResponse], summary="채팅 이력 조회")
async def list_messages(session_id: UUID):
    """
    특정 채팅 세션의 모든 메시지 이력을 시간순으로 조회합니다.
    """
    messages = await ChatMessage.filter(session_id=session_id).order_by("created_at")
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT, summary="메시지 삭제")
async def delete_message(message_id: UUID):
    """
    특정 메시지를 삭제합니다.
    """
    message = await ChatMessage.get_or_none(id=message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="메시지를 찾을 수 없습니다.")
    
    await message.delete()
    return
