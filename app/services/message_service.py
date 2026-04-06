"""
Message Service

채팅 메시지 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.models.messages import ChatMessage
from app.repositories.message_repository import MessageRepository


class MessageService:
    """채팅 메시지 비즈니스 로직"""

    def __init__(self):
        self.repository = MessageRepository()

    async def get_message(self, message_id: UUID) -> ChatMessage:
        """메시지 조회"""
        message = await self.repository.get_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없습니다.",
            )
        return message

    async def get_messages_by_session(self, session_id: UUID, limit: int | None = None) -> list[ChatMessage]:
        """세션의 모든 메시지 조회"""
        return await self.repository.get_by_session(session_id, limit)

    async def get_recent_messages(self, session_id: UUID, limit: int = 10) -> list[ChatMessage]:
        """세션의 최근 메시지 조회"""
        return await self.repository.get_recent_by_session(session_id, limit)

    async def create_user_message(self, session_id: UUID, content: str) -> ChatMessage:
        """사용자 메시지 생성"""
        return await self.repository.create_user_message(session_id, content)

    async def create_assistant_message(self, session_id: UUID, content: str) -> ChatMessage:
        """어시스턴트 메시지 생성"""
        return await self.repository.create_assistant_message(session_id, content)

    async def delete_message(self, message_id: UUID) -> None:
        """메시지 삭제 (soft delete)"""
        message = await self.get_message(message_id)
        await self.repository.soft_delete(message)
