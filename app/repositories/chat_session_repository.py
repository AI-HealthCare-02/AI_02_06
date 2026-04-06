"""
ChatSession Repository

chat_sessions 테이블 데이터 접근 계층
"""

from uuid import UUID, uuid4

from app.models.chat_sessions import ChatSession


class ChatSessionRepository:
    """ChatSession DB 저장소"""

    async def get_by_id(self, session_id: UUID) -> ChatSession | None:
        """세션 ID로 조회 (soft delete 제외)"""
        return await ChatSession.filter(
            id=session_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_account(self, account_id: UUID) -> list[ChatSession]:
        """계정의 모든 채팅 세션 조회"""
        return (
            await ChatSession.filter(
                account_id=account_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .all()
        )

    async def get_by_profile(self, profile_id: UUID) -> list[ChatSession]:
        """프로필의 채팅 세션 조회"""
        return (
            await ChatSession.filter(
                profile_id=profile_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .all()
        )

    async def get_by_medication(self, medication_id: UUID) -> list[ChatSession]:
        """약품 관련 채팅 세션 조회"""
        return (
            await ChatSession.filter(
                medication_id=medication_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .all()
        )

    async def create(
        self,
        account_id: UUID,
        profile_id: UUID,
        medication_id: UUID | None = None,
        title: str | None = None,
    ) -> ChatSession:
        """새 채팅 세션 생성"""
        return await ChatSession.create(
            id=uuid4(),
            account_id=account_id,
            profile_id=profile_id,
            medication_id=medication_id,
            title=title,
        )

    async def update(self, session: ChatSession, **kwargs) -> ChatSession:
        """채팅 세션 정보 업데이트"""
        await session.update_from_dict(kwargs).save()
        return session

    async def soft_delete(self, session: ChatSession) -> ChatSession:
        """채팅 세션 소프트 삭제"""
        from datetime import datetime

        from app.core import config

        session.deleted_at = datetime.now(tz=config.TIMEZONE)
        await session.save()
        return session
