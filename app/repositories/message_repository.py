"""
Message Repository

messages 테이블 데이터 접근 계층
"""

from uuid import UUID, uuid4

from app.models.messages import ChatMessage, SenderType


class MessageRepository:
    """ChatMessage DB 저장소"""

    async def get_by_id(self, message_id: UUID) -> ChatMessage | None:
        """메시지 ID로 조회 (soft delete 제외)"""
        return await ChatMessage.filter(
            id=message_id,
            deleted_at__isnull=True,
        ).first()

    async def get_by_session(self, session_id: UUID, limit: int | None = None) -> list[ChatMessage]:
        """세션의 모든 메시지 조회 (시간순)"""
        query = ChatMessage.filter(
            session_id=session_id,
            deleted_at__isnull=True,
        ).order_by("created_at")

        if limit:
            query = query.limit(limit)

        return await query.all()

    async def get_recent_by_session(self, session_id: UUID, limit: int = 10) -> list[ChatMessage]:
        """세션의 최근 메시지 조회"""
        return (
            await ChatMessage.filter(
                session_id=session_id,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .limit(limit)
            .all()
        )

    async def create(
        self,
        session_id: UUID,
        sender_type: SenderType,
        content: str,
    ) -> ChatMessage:
        """새 메시지 생성"""
        return await ChatMessage.create(
            id=uuid4(),
            session_id=session_id,
            sender_type=sender_type,
            content=content,
        )

    async def create_user_message(self, session_id: UUID, content: str) -> ChatMessage:
        """사용자 메시지 생성"""
        return await self.create(session_id, SenderType.USER, content)

    async def create_assistant_message(self, session_id: UUID, content: str) -> ChatMessage:
        """어시스턴트 메시지 생성"""
        return await self.create(session_id, SenderType.ASSISTANT, content)

    async def soft_delete(self, message: ChatMessage) -> ChatMessage:
        """메시지 소프트 삭제"""
        from datetime import datetime

        from app.core import config

        message.deleted_at = datetime.now(tz=config.TIMEZONE)
        await message.save()
        return message


class MessageFeedbackRepository:
    """메시지 피드백(좋아요/싫어요) 저장소"""

    async def get_by_message_id(self, message_id: UUID):
        """특정 메시지의 피드백 조회"""
        from app.models.message_feedbacks import MessageFeedback

        return await MessageFeedback.filter(message_id=message_id).first()

    async def create_or_update(
        self,
        message_id: UUID,
        is_helpful: bool,
        feedback_text: str | None = None,
        metadata: dict | None = None,
    ):
        """피드백 생성 또는 업데이트 (1:1 관계이므로 기존 것 있으면 갱신)"""
        from app.models.message_feedbacks import MessageFeedback

        feedback, created = await MessageFeedback.get_or_create(
            message_id=message_id,
            defaults={
                "is_helpful": is_helpful,
                "feedback_text": feedback_text,
                "metadata": metadata,
            },
        )

        if not created:
            feedback.is_helpful = is_helpful
            feedback.feedback_text = feedback_text
            if metadata:
                feedback.metadata = metadata
            await feedback.save()

        return feedback
