"""Chat session repository module.

This module provides data access layer for the chat_sessions table,
handling conversation session management operations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core import config
from app.models.chat_sessions import ChatSession


class ChatSessionRepository:
    """Chat session database repository for conversation management."""

    async def get_by_id(self, session_id: UUID) -> ChatSession | None:
        """Get session by ID (excluding soft deleted).

        Args:
            session_id: Session UUID.

        Returns:
            ChatSession | None: Session if found, None otherwise.
        """
        return await ChatSession.filter(
            id=session_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_account(self, account_id: UUID) -> list[ChatSession]:
        """Get all chat sessions for an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[ChatSession]: List of chat sessions.
        """
        return (
            await ChatSession
            .filter(
                account_id=account_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .all()
        )

    async def get_by_profile(self, profile_id: UUID) -> list[ChatSession]:
        """Get chat sessions for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[ChatSession]: List of chat sessions.
        """
        return (
            await ChatSession
            .filter(
                profile_id=profile_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .all()
        )

    async def create(
        self,
        account_id: UUID,
        profile_id: UUID,
        title: str | None = None,
    ) -> ChatSession:
        """Create new chat session.

        Args:
            account_id: Account UUID.
            profile_id: Profile UUID.
            title: Optional session title.

        Returns:
            ChatSession: Created session.
        """
        return await ChatSession.create(
            id=uuid4(),
            account_id=account_id,
            profile_id=profile_id,
            title=title,
        )

    async def update(self, session: ChatSession, **kwargs) -> ChatSession:
        """Update chat session information.

        Args:
            session: Session to update.
            **kwargs: Fields to update.

        Returns:
            ChatSession: Updated session.
        """
        await session.update_from_dict(kwargs).save()
        return session

    async def update_summary(self, session_id: UUID, summary: str) -> int:
        """세션 요약 + 갱신 timestamp UPDATE — compact RQ job 종료 시 호출.

        Args:
            session_id: 갱신 대상 세션 UUID.
            summary: SessionCompactService 가 만든 마크다운 요약 본문.

        Returns:
            UPDATE 된 row 수 (정상이면 1, 세션 없으면 0).
        """
        return await ChatSession.filter(id=session_id, deleted_at__isnull=True).update(
            summary=summary,
            summary_updated_at=datetime.now(UTC),
        )

    async def soft_delete(self, session: ChatSession) -> ChatSession:
        """Soft delete chat session.

        Args:
            session: Session to delete.

        Returns:
            ChatSession: Soft deleted session.
        """
        session.deleted_at = datetime.now(tz=config.TIMEZONE)
        await session.save()
        return session

    async def bulk_soft_delete_by_account(self, account_id: UUID) -> int:
        """계정 소유의 모든 active chat session 을 일괄 soft delete.

        회원탈퇴 흐름의 일부. account_id 컬럼을 직접 갖는 세션만 처리하며,
        profile_id 만 가진 세션은 별도로 ``bulk_soft_delete_by_profile`` 호출.

        Args:
            account_id: 대상 계정 UUID.

        Returns:
            새로 deleted_at 이 채워진 row 수.
        """
        return await ChatSession.filter(
            account_id=account_id,
            deleted_at__isnull=True,
        ).update(deleted_at=datetime.now(tz=config.TIMEZONE))

    async def bulk_soft_delete_by_profile(self, profile_id: UUID) -> int:
        """프로필 단위 chat session 일괄 soft delete (Profile cascade 흐름).

        Args:
            profile_id: 대상 프로필 UUID.

        Returns:
            새로 deleted_at 이 채워진 row 수.
        """
        return await ChatSession.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).update(deleted_at=datetime.now(tz=config.TIMEZONE))
