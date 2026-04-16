"""
Message Service

채팅 메시지 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import HTTPException, status

from ai_worker.utils.rag import RAGGenerator
from app.models.messages import ChatMessage
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import MessageRepository


class MessageService:
    """채팅 메시지 비즈니스 로직"""

    def __init__(self):
        self.repository = MessageRepository()
        self.session_repository = ChatSessionRepository()

    async def _verify_session_ownership(self, session_id: UUID, account_id: UUID) -> None:
        """채팅 세션 소유권 검증"""
        session = await self.session_repository.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅 세션을 찾을 수 없습니다.",
            )
        if session.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 채팅 세션에 대한 접근 권한이 없습니다.",
            )

    async def _verify_message_ownership(self, message: ChatMessage, account_id: UUID) -> None:
        """메시지 소유권 검증 (세션을 통해)"""
        await message.fetch_related("session")
        if message.session.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 메시지에 대한 접근 권한이 없습니다.",
            )

    async def get_message(self, message_id: UUID) -> ChatMessage:
        """메시지 조회"""
        message = await self.repository.get_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="메시지를 찾을 수 없습니다.",
            )
        return message

    async def get_message_with_owner_check(self, message_id: UUID, account_id: UUID) -> ChatMessage:
        """소유권 검증 후 메시지 조회"""
        message = await self.get_message(message_id)
        await self._verify_message_ownership(message, account_id)
        return message

    async def get_messages_by_session(self, session_id: UUID, limit: int | None = None) -> list[ChatMessage]:
        """세션의 모든 메시지 조회"""
        return await self.repository.get_by_session(session_id, limit)

    async def get_messages_by_session_with_owner_check(
        self, session_id: UUID, account_id: UUID, limit: int | None = None
    ) -> list[ChatMessage]:
        """소유권 검증 후 세션의 모든 메시지 조회"""
        await self._verify_session_ownership(session_id, account_id)
        return await self.repository.get_by_session(session_id, limit)

    async def get_recent_messages(self, session_id: UUID, limit: int = 10) -> list[ChatMessage]:
        """세션의 최근 메시지 조회"""
        return await self.repository.get_recent_by_session(session_id, limit)

    async def create_user_message(self, session_id: UUID, content: str) -> ChatMessage:
        """사용자 메시지 생성"""
        return await self.repository.create_user_message(session_id, content)

    async def create_user_message_with_owner_check(
        self, session_id: UUID, account_id: UUID, content: str
    ) -> ChatMessage:
        """소유권 검증 후 사용자 메시지 생성"""
        await self._verify_session_ownership(session_id, account_id)
        return await self.repository.create_user_message(session_id, content)

    async def create_assistant_message(self, session_id: UUID, content: str) -> ChatMessage:
        """어시스턴트 메시지 생성"""
        return await self.repository.create_assistant_message(session_id, content)

    async def ask_and_reply(self, session_id: UUID, content: str) -> tuple[ChatMessage, ChatMessage]:
        """
        사용자 메시지 저장, 약사 페르소나에 맞춰 응답 생성 후,
        사용자 메시지와 약사 메시지를 모두 반환합니다.
        """
        user_msg = await self.repository.create_user_message(session_id, content)

        recent = await self.repository.get_recent_by_session(session_id, limit=10)
        history = [
            {"role": "user" if m.sender_type == "USER" else "assistant", "content": m.content}
            for m in recent
            if m.id != user_msg.id
        ]

        # "다정한 퍼스널 약사" 페르소나 적용
        system_prompt = (
            "당신은 친절하고 상냥한 '퍼스널 약사'입니다. "
            "사용자의 복약 관련 질문에 대해 따뜻하고 이해하기 쉬운 언어로 답변해주세요. "
            "답변 시에는 항상 '~해요', '~일까요?' 와 같은 부드러운 구어체를 사용해주세요. "
            "복약, 영양제 추천, 건강 정보 등 서비스의 핵심 기능에 관련된 질문에 집중해주세요. "
            "만약 날씨, 정치, 연예 등 복약과 관련 없는 질문을 받는다면, "
            "정중하게 답변을 거절하고 '저는 복약 및 건강 정보에 대해 안내해 드리는 약사이니, "
            "영양제 추천이나 복약 관련 질문을 해주시면 더 잘 도와드릴 수 있어요.' 와 같이 서비스를 안내해주세요. "
            "사용자와의 대화는 항상 긍정적이고 편안한 분위기를 유지해주세요."
        )

        try:
            rag = RAGGenerator()
            # 현재 사용자 메시지를 히스토리에 추가
            messages = history + [{"role": "user", "content": content}]
            reply = await rag.generate_chat_response(messages, system_prompt=system_prompt)
        except (ValueError, RuntimeError) as e:
            # 실패를 201 성공으로 숨기지 않기 위해, 저장한 user_msg를 정리하고 에러를 표면화합니다.
            await self.repository.soft_delete(user_msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "ai_unavailable",
                    "error_description": "현재 AI 응답을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
                    "cause": str(e),
                },
            ) from e

        assistant_msg = await self.repository.create_assistant_message(session_id, reply)
        return user_msg, assistant_msg

    async def delete_message(self, message_id: UUID) -> None:
        """메시지 삭제 (soft delete)"""
        message = await self.get_message(message_id)
        await self.repository.soft_delete(message)

    async def delete_message_with_owner_check(self, message_id: UUID, account_id: UUID) -> None:
        """소유권 검증 후 메시지 삭제 (soft delete)"""
        message = await self.get_message_with_owner_check(message_id, account_id)
        await self.repository.soft_delete(message)
