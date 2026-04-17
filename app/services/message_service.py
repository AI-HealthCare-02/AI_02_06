"""Message service module.

This module provides business logic for chat message management operations
including creation, AI response generation, and ownership verification.
"""

from uuid import UUID

from fastapi import HTTPException, status

# TODO: Replace RAGGenerator with RAGPipeline after Task 2 implementation
from ai_worker.utils.rag import RAGGenerator
from app.models.messages import ChatMessage
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import MessageRepository


class MessageService:
    """Message business logic service for chat conversation management."""

    def __init__(self):
        self.repository = MessageRepository()
        self.session_repository = ChatSessionRepository()

    async def _verify_session_ownership(self, session_id: UUID, account_id: UUID) -> None:
        """Verify chat session ownership.

        Args:
            session_id: Session UUID to verify.
            account_id: Account UUID that should own the session.

        Raises:
            HTTPException: If session not found or access denied.
        """
        session = await self.session_repository.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )
        if session.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session.",
            )

    async def _verify_message_ownership(self, message: ChatMessage, account_id: UUID) -> None:
        """Verify message ownership through session.

        Args:
            message: Message to verify ownership for.
            account_id: Account UUID that should own the message.

        Raises:
            HTTPException: If access denied to message.
        """
        await message.fetch_related("session")
        if message.session.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this message.",
            )

    async def get_message(self, message_id: UUID) -> ChatMessage:
        """Get message by ID.

        Args:
            message_id: Message UUID.

        Returns:
            ChatMessage: Message object.

        Raises:
            HTTPException: If message not found.
        """
        message = await self.repository.get_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found.",
            )
        return message

    async def get_message_with_owner_check(self, message_id: UUID, account_id: UUID) -> ChatMessage:
        """Get message with ownership verification.

        Args:
            message_id: Message UUID.
            account_id: Account UUID for ownership check.

        Returns:
            ChatMessage: Message if owned by account.
        """
        message = await self.get_message(message_id)
        await self._verify_message_ownership(message, account_id)
        return message

    async def get_messages_by_session(self, session_id: UUID, limit: int | None = None) -> list[ChatMessage]:
        """Get all messages in a session.

        Args:
            session_id: Session UUID.
            limit: Optional limit on number of messages.

        Returns:
            list[ChatMessage]: List of messages in the session.
        """
        return await self.repository.get_by_session(session_id, limit)

    async def get_messages_by_session_with_owner_check(
        self, session_id: UUID, account_id: UUID, limit: int | None = None
    ) -> list[ChatMessage]:
        """Get all messages in a session with ownership verification.

        Args:
            session_id: Session UUID.
            account_id: Account UUID for ownership check.
            limit: Optional limit on number of messages.

        Returns:
            list[ChatMessage]: List of messages if session is owned by account.
        """
        await self._verify_session_ownership(session_id, account_id)
        return await self.repository.get_by_session(session_id, limit)

    async def get_recent_messages(self, session_id: UUID, limit: int = 10) -> list[ChatMessage]:
        """Get recent messages in a session.

        Args:
            session_id: Session UUID.
            limit: Maximum number of messages to retrieve.

        Returns:
            list[ChatMessage]: List of recent messages.
        """
        return await self.repository.get_recent_by_session(session_id, limit)

    async def create_user_message(self, session_id: UUID, content: str) -> ChatMessage:
        """Create user message.

        Args:
            session_id: Session UUID.
            content: Message content.

        Returns:
            ChatMessage: Created user message.
        """
        return await self.repository.create_user_message(session_id, content)

    async def create_user_message_with_owner_check(
        self, session_id: UUID, account_id: UUID, content: str
    ) -> ChatMessage:
        """Create user message with ownership verification.

        Args:
            session_id: Session UUID.
            account_id: Account UUID for ownership check.
            content: Message content.

        Returns:
            ChatMessage: Created user message if session is owned by account.
        """
        await self._verify_session_ownership(session_id, account_id)
        return await self.repository.create_user_message(session_id, content)

    async def create_assistant_message(self, session_id: UUID, content: str) -> ChatMessage:
        """Create assistant message.

        Args:
            session_id: Session UUID.
            content: Message content.

        Returns:
            ChatMessage: Created assistant message.
        """
        return await self.repository.create_assistant_message(session_id, content)

    async def ask_and_reply(self, session_id: UUID, content: str) -> tuple[ChatMessage, ChatMessage]:
        """Save user message, generate pharmacist persona response, and return both messages.

        Args:
            session_id: Session UUID.
            content: User message content.

        Returns:
            tuple[ChatMessage, ChatMessage]: (user_message, assistant_message)

        Raises:
            HTTPException: If AI response generation fails.
        """
        user_msg = await self.repository.create_user_message(session_id, content)

        recent = await self.repository.get_recent_by_session(session_id, limit=10)
        history = [
            {"role": "user" if m.sender_type == "USER" else "assistant", "content": m.content}
            for m in recent
            if m.id != user_msg.id
        ]

        # Apply "friendly personal pharmacist" persona
        system_prompt = (
            "You are a kind and friendly 'Personal Pharmacist'. "
            "Please answer users' medication-related questions in warm and easy-to-understand language. "
            "Always use gentle conversational tone like '~해요', '~일까요?' in Korean. "
            "Focus on questions related to core service functions such as medication, "
            "supplement recommendations, and health information. "
            "If you receive questions unrelated to medication such as weather, politics, or entertainment, "
            "politely decline and guide them like 'I'm a pharmacist who provides guidance on "
            "medication and health information, so I can help you better if you ask about "
            "supplement recommendations or medication-related questions.' "
            "Always maintain a positive and comfortable atmosphere in conversations with users."
        )

        try:
            rag = RAGGenerator()
            # 현재 사용자 메시지를 히스토리에 추가
            messages = [*history, {"role": "user", "content": content}]
            reply = await rag.generate_chat_response(messages, system_prompt=system_prompt)
        except (ValueError, RuntimeError) as e:
            # Clean up saved user message on failure and surface the error
            await self.repository.soft_delete(user_msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "ai_unavailable",
                    "error_description": "AI response is currently unavailable. Please try again later.",
                    "cause": str(e),
                },
            ) from e

        assistant_msg = await self.repository.create_assistant_message(session_id, reply)
        return user_msg, assistant_msg

    async def delete_message(self, message_id: UUID) -> None:
        """Delete message (soft delete).

        Args:
            message_id: Message UUID to delete.
        """
        message = await self.get_message(message_id)
        await self.repository.soft_delete(message)

    async def delete_message_with_owner_check(self, message_id: UUID, account_id: UUID) -> None:
        """Delete message with ownership verification (soft delete).

        Args:
            message_id: Message UUID to delete.
            account_id: Account UUID for ownership check.
        """
        message = await self.get_message_with_owner_check(message_id, account_id)
        await self.repository.soft_delete(message)
