"""
ChatSession Service

채팅 세션 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.models.chat_sessions import ChatSession
from app.repositories.chat_session_repository import ChatSessionRepository


class ChatSessionService:
    """채팅 세션 비즈니스 로직"""

    def __init__(self):
        self.repository = ChatSessionRepository()

    async def get_session(self, session_id: UUID) -> ChatSession:
        """채팅 세션 조회"""
        session = await self.repository.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅 세션을 찾을 수 없습니다.",
            )
        return session

    async def get_sessions_by_account(self, account_id: UUID) -> list[ChatSession]:
        """계정의 모든 채팅 세션 조회"""
        return await self.repository.get_all_by_account(account_id)

    async def get_sessions_by_profile(self, profile_id: UUID) -> list[ChatSession]:
        """프로필의 채팅 세션 조회"""
        return await self.repository.get_by_profile(profile_id)

    async def create_session(
        self,
        account_id: UUID,
        profile_id: UUID,
        medication_id: UUID | None = None,
        title: str | None = None,
    ) -> ChatSession:
        """채팅 세션 생성"""
        return await self.repository.create(
            account_id=account_id,
            profile_id=profile_id,
            medication_id=medication_id,
            title=title,
        )

    async def update_session_title(self, session_id: UUID, title: str) -> ChatSession:
        """채팅 세션 제목 업데이트"""
        session = await self.get_session(session_id)
        return await self.repository.update(session, title=title)

    async def delete_session(self, session_id: UUID) -> None:
        """채팅 세션 삭제 (soft delete)"""
        session = await self.get_session(session_id)
        await self.repository.soft_delete(session)
