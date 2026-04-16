"""Chat session service module.

This module provides business logic for chat session management operations
including creation, updates, and ownership verification.
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.models.chat_sessions import ChatSession
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.profile_repository import ProfileRepository


class ChatSessionService:
    """Chat session business logic service for conversation management."""

    def __init__(self):
        self.repository = ChatSessionRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """Verify profile ownership.

        Args:
            profile_id: Profile UUID to verify.
            account_id: Account UUID that should own the profile.

        Raises:
            HTTPException: If profile not found or access denied.
        """
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this profile.",
            )

    async def _verify_session_ownership(self, session: ChatSession, account_id: UUID) -> None:
        """Verify chat session ownership.

        Args:
            session: Chat session to verify ownership for.
            account_id: Account UUID that should own the session.

        Raises:
            HTTPException: If access denied to session.
        """
        if session.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session.",
            )

    async def get_session(self, session_id: UUID) -> ChatSession:
        """Get chat session by ID.

        Args:
            session_id: Session UUID.

        Returns:
            ChatSession: Chat session object.

        Raises:
            HTTPException: If session not found.
        """
        session = await self.repository.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )
        return session

    async def get_session_with_owner_check(self, session_id: UUID, account_id: UUID) -> ChatSession:
        """Get chat session with ownership verification.

        Args:
            session_id: Session UUID.
            account_id: Account UUID for ownership check.

        Returns:
            ChatSession: Chat session if owned by account.
        """
        session = await self.get_session(session_id)
        await self._verify_session_ownership(session, account_id)
        return session

    async def get_sessions_by_account(self, account_id: UUID) -> list[ChatSession]:
        """Get all chat sessions for an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[ChatSession]: List of chat sessions.
        """
        return await self.repository.get_all_by_account(account_id)

    async def get_sessions_by_profile(self, profile_id: UUID) -> list[ChatSession]:
        """Get chat sessions for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[ChatSession]: List of chat sessions.
        """
        return await self.repository.get_by_profile(profile_id)

    async def get_sessions_by_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[ChatSession]:
        """Get chat sessions for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[ChatSession]: List of chat sessions if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_by_profile(profile_id)

    async def create_session(
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
            ChatSession: Created chat session.
        """
        return await self.repository.create(
            account_id=account_id,
            profile_id=profile_id,
            medication_id=medication_id,
            title=title,
        )

    async def create_session_with_owner_check(
        self,
        account_id: UUID,
        profile_id: UUID,
        medication_id: UUID | None = None,
        title: str | None = None,
    ) -> ChatSession:
        """Create chat session with ownership verification.

        Args:
            account_id: Account UUID.
            profile_id: Profile UUID.
            medication_id: Optional medication UUID.
            title: Optional session title.

        Returns:
            ChatSession: Created chat session if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_session(
            account_id=account_id,
            profile_id=profile_id,
            medication_id=medication_id,
            title=title,
        )

    async def update_session_title(self, session_id: UUID, title: str) -> ChatSession:
        """Update chat session title.

        Args:
            session_id: Session UUID.
            title: New session title.

        Returns:
            ChatSession: Updated chat session.
        """
        session = await self.get_session(session_id)
        return await self.repository.update(session, title=title)

    async def delete_session(self, session_id: UUID) -> None:
        """Delete chat session (soft delete).

        Args:
            session_id: Session UUID to delete.
        """
        session = await self.get_session(session_id)
        await self.repository.soft_delete(session)

    async def delete_session_with_owner_check(self, session_id: UUID, account_id: UUID) -> None:
        """Delete chat session with ownership verification (soft delete).

        Args:
            session_id: Session UUID to delete.
            account_id: Account UUID for ownership check.
        """
        session = await self.get_session_with_owner_check(session_id, account_id)
        await self.repository.soft_delete(session)
