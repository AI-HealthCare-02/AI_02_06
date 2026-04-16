"""Chat session repository module.

This module provides data access layer for the chat_sessions table,
handling conversation session management operations.
"""

from uuid import UUID, uuid4

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

    async def get_by_medication(self, medication_id: UUID) -> list[ChatSession]:
        """Get medication-related chat sessions.

        Args:
            medication_id: Medication UUID.

        Returns:
            list[ChatSession]: List of medication-related sessions.
        """
        return (
            await ChatSession
            .filter(
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
        """Create new chat session.

        Args:
            account_id: Account UUID.
            profile_id: Profile UUID.
            medication_id: Optional medication UUID.
            title: Optional session title.

        Returns:
            ChatSession: Created session.
        """
        return await ChatSession.create(
            id=uuid4(),
            account_id=account_id,
            profile_id=profile_id,
            medication_id=medication_id,
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

    async def soft_delete(self, session: ChatSession) -> ChatSession:
        """Soft delete chat session.

        Args:
            session: Session to delete.

        Returns:
            ChatSession: Soft deleted session.
        """
        from datetime import datetime

        from app.core import config

        session.deleted_at = datetime.now(tz=config.TIMEZONE)
        await session.save()
        return session
