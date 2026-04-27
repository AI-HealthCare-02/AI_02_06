"""Message service module.

This module provides business logic for chat message management operations
including creation, AI response generation, and ownership verification.
"""

from datetime import UTC, datetime
import json
import logging
import math
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.tools import AskPending, AskResult, PendingTurn, RouteResult, ToolCall
from app.models.messages import ChatMessage
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import MessageRepository
from app.services.tools.pending import DEFAULT_TTL_SEC, PendingTurnStore
from app.services.tools.rq_adapters import (
    generate_chat_response_via_rq,
    route_intent_via_rq,
    run_tool_calls_via_rq,
)

logger = logging.getLogger(__name__)

_HISTORY_LIMIT = 10
_STATUS_OK = "ok"
_STATUS_DENIED = "denied"
_GEOLOCATION_DENIED_MESSAGE = "Permission denied: user rejected geolocation"

# HTTP status codes referenced inside ``resolve_pending_turn`` — the
# ``status`` parameter shadows ``fastapi.status`` in that method, so the
# symbolic aliases are imported up-front to avoid an inline alias.
_HTTP_400_BAD_REQUEST = 400
_HTTP_403_FORBIDDEN = 403
_HTTP_410_GONE = 410


def _is_valid_coords(lat: float | None, lng: float | None) -> bool:
    """``lat``/``lng`` 가 유한한 숫자값인지 검증.

    None / NaN / Infinity / 비숫자 모두 거부 — 잘못된 좌표가 ai-worker 까지
    내려가 Kakao API 호출에서 ValueError 로 터지는 것을 callback 진입 단계에서
    명확한 400 으로 끊는다.
    """
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return False
    if isinstance(lat, bool) or isinstance(lng, bool):  # bool 은 int 의 서브클래스
        return False
    return math.isfinite(lat) and math.isfinite(lng)


def _chat_messages_to_history(messages: list[ChatMessage]) -> list[dict[str, str]]:
    """Map stored ChatMessages (newest-first) to chronological LLM history."""
    chronological = list(reversed(messages))
    return [{"role": "user" if m.sender_type == "USER" else "assistant", "content": m.content} for m in chronological]


def _tool_call_to_worker_dict(call: ToolCall, *, geolocation: dict[str, float] | None = None) -> dict[str, Any]:
    """Render a ``ToolCall`` DTO into the pickle-safe dict the worker expects."""
    payload: dict[str, Any] = {
        "tool_call_id": call.tool_call_id,
        "name": call.name,
        "arguments": call.arguments,
    }
    if geolocation is not None:
        payload["geolocation"] = geolocation
    return payload


def _tool_result_message(tool_call_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Wrap one tool result as the ``role="tool"`` message the LLM expects."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": json.dumps(result, ensure_ascii=False),
    }


class MessageService:
    """Message business logic service for chat conversation management."""

    def __init__(
        self,
        *,
        pending_store: PendingTurnStore | None = None,
        queue: Any = None,
    ) -> None:
        self.repository = MessageRepository()
        self.session_repository = ChatSessionRepository()
        self._pending_store = pending_store
        self._queue = queue

    def _get_queue(self) -> Any:
        """Lazy-init the RQ ``"ai"`` queue shared with the RAG pipeline.

        Kept as an instance method (not a singleton) so tests can inject
        a stub queue via ``MessageService(queue=...)``.
        """
        if self._queue is None:
            from rq import Queue

            from app.core.config import config
            from app.core.redis_client import make_sync_redis

            redis_conn = make_sync_redis(config.REDIS_URL)
            self._queue = Queue("ai", connection=redis_conn)
        return self._queue

    def _get_pending_store(self) -> PendingTurnStore:
        """Lazy-init the Redis-backed pending-turn store."""
        if self._pending_store is None:
            from app.core.config import config
            from app.core.redis_client import make_async_redis
            from app.services.tools.pending import RedisPendingTurnStore

            self._pending_store = RedisPendingTurnStore(redis=make_async_redis(config.REDIS_URL))
        return self._pending_store

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

    # ── 한 턴 라우팅 진입점 (Router LLM tool-calling) ───────────────────
    # 흐름: ownership -> Router LLM -> kind='text' 직답 persist
    #       또는 tool_calls 분기 (eager 즉시 실행 / geo 포함 시 PendingTurn)
    async def ask_with_tools(
        self,
        *,
        session_id: UUID,
        account_id: UUID,
        content: str,
    ) -> AskResult:
        """Route one user turn through the Router LLM and fan out.

        Three branches:

        - **text** — Router produced a natural-language reply without
          invoking any tool (도메인 외 거절, 명확화 질문, 일반 인사).
          Persist 사용자 turn + Router 의 text 를 그대로 assistant turn 으로.
        - **tool_calls, all eager** — every tool call can run now
          (keyword + RAG retrieval). Execute in parallel, feed results
          back to the 2nd LLM, persist both turns.
        - **tool_calls, any geo** — at least one call needs the user's
          GPS. Run any eager calls immediately so they are not re-run
          on callback, then snapshot the turn into the pending store
          and hand the client an ``AskPending`` for the GPS round-trip.

        Args:
            session_id: Chat session UUID.
            account_id: Caller account UUID (for ownership check).
            content: User message content.

        Returns:
            ``AskResult`` — shape differs per branch; see DTO docstring.

        Raises:
            HTTPException: Session ownership violations bubble up.
        """
        await self._verify_session_ownership(session_id, account_id)

        recent = await self.repository.get_recent_by_session(session_id, limit=_HISTORY_LIMIT)
        history = _chat_messages_to_history(recent)
        route_messages = [*history, {"role": "user", "content": content}]

        queue = self._get_queue()

        route = await route_intent_via_rq(messages=route_messages, queue=queue)
        logger.info("[ToolCalling] route kind=%s calls=%d", route.kind, len(route.tool_calls))

        if route.kind == "text":
            return await self._persist_router_text_turn(session_id, content, route.text)

        eager_calls = [tc for tc in route.tool_calls if not tc.needs_geolocation]
        geo_calls = [tc for tc in route.tool_calls if tc.needs_geolocation]

        eager_results: dict[str, Any] = {}
        if eager_calls:
            eager_payload = [_tool_call_to_worker_dict(tc) for tc in eager_calls]
            eager_results = await run_tool_calls_via_rq(calls=eager_payload, queue=queue)

        if geo_calls:
            return await self._park_pending_turn(
                session_id=session_id,
                account_id=account_id,
                content=content,
                route=route,
                eager_results=eager_results,
            )

        return await self._finalize_tool_turn(
            session_id=session_id,
            content=content,
            history=history,
            route=route,
            tool_results=eager_results,
        )

    async def _persist_router_text_turn(
        self,
        session_id: UUID,
        content: str,
        text: str,
    ) -> AskResult:
        """Router LLM 이 직접 답변한 (text) 턴을 user/assistant 메시지로 persist."""
        user_msg = await self.repository.create_user_message(session_id, content)
        assistant_msg = await self.repository.create_assistant_message(session_id, text)
        return AskResult(user_message=user_msg, assistant_message=assistant_msg, pending=None)

    async def _park_pending_turn(
        self,
        *,
        session_id: UUID,
        account_id: UUID,
        content: str,
        route: RouteResult,
        eager_results: dict[str, Any],
    ) -> AskResult:
        """Persist the user turn and hand out an ``AskPending`` handle."""
        user_msg = await self.repository.create_user_message(session_id, content)

        messages_snapshot = [
            {"role": "user", "content": content},
            route.assistant_message or {"role": "assistant", "content": None, "tool_calls": []},
        ]
        pending = PendingTurn(
            turn_id="",
            session_id=str(session_id),
            account_id=str(account_id),
            messages_snapshot=messages_snapshot,
            tool_calls=route.tool_calls,
            eager_results=eager_results,
            created_at=datetime.now(UTC),
        )
        store = self._get_pending_store()
        turn_id = await store.create(pending)
        geo_count = len(route.tool_calls) - len(eager_results)
        logger.info("[ToolCalling] pending turn=%s eager=%d geo=%d", turn_id, len(eager_results), geo_count)

        return AskResult(
            user_message=user_msg,
            assistant_message=None,
            pending=AskPending(turn_id=turn_id, ttl_sec=DEFAULT_TTL_SEC),
        )

    async def _finalize_tool_turn(
        self,
        *,
        session_id: UUID,
        content: str,
        history: list[dict[str, str]],
        route: RouteResult,
        tool_results: dict[str, Any],
    ) -> AskResult:
        """Run the 2nd LLM with tool results and persist both turns."""
        assistant_with_calls = route.assistant_message or {"role": "assistant", "content": None, "tool_calls": []}
        tool_messages = [_tool_result_message(call_id, result) for call_id, result in tool_results.items()]

        second_messages = [
            *history,
            {"role": "user", "content": content},
            assistant_with_calls,
            *tool_messages,
        ]
        completion = await generate_chat_response_via_rq(
            messages=second_messages,
            system_prompt=None,
            queue=self._get_queue(),
        )
        answer = completion.get("answer", "")

        user_msg = await self.repository.create_user_message(session_id, content)
        assistant_msg = await self.repository.create_assistant_message(session_id, answer)
        return AskResult(user_message=user_msg, assistant_message=assistant_msg, pending=None)

    # ── pending GPS 턴 마무리 (오케스트레이션) ───────────────────────────
    # 흐름: 입력 검증 -> claim+ownership -> geo 결과 수집
    #       -> 2nd LLM 호출 -> assistant message persist
    async def resolve_pending_turn(
        self,
        *,
        turn_id: str,
        account_id: UUID | str,
        status: str,
        lat: float | None,
        lng: float | None,
    ) -> AskResult:
        """Complete a turn that was waiting on a GPS callback.

        Args:
            turn_id: Id returned to the client as ``AskPending.turn_id``.
            account_id: Caller account id (string compare against pending owner).
            status: ``"ok"`` (user allowed GPS) or ``"denied"``.
            lat: Latitude (WGS84) when ``status="ok"``.
            lng: Longitude (WGS84) when ``status="ok"``.

        Returns:
            ``AskResult`` with only ``assistant_message`` set — user turn 은
            pending 생성 시점에 이미 저장됨.

        Raises:
            HTTPException: 400 / 403 / 410 (helper 들이 던짐).
        """
        self._validate_resolve_payload(status, lat, lng)
        pending = await self._claim_and_authorize(turn_id, account_id)
        results = await self._collect_tool_results(pending, status=status, lat=lat, lng=lng)

        completion = await generate_chat_response_via_rq(
            messages=[
                *pending.messages_snapshot,
                *(_tool_result_message(cid, res) for cid, res in results.items()),
            ],
            system_prompt=None,
            queue=self._get_queue(),
        )
        answer = completion.get("answer", "")

        session_uuid = UUID(pending.session_id)
        assistant_msg = await self.repository.create_assistant_message(session_uuid, answer)
        logger.info("[ToolCalling] resolved turn=%s status=%s", turn_id, status)
        return AskResult(user_message=None, assistant_message=assistant_msg, pending=None)

    @staticmethod
    def _validate_resolve_payload(status: str, lat: float | None, lng: float | None) -> None:
        """status='ok' 인데 lat/lng 가 유효하지 않으면 즉시 400 — claim 낭비 방지."""
        if status == _STATUS_OK and not _is_valid_coords(lat, lng):
            raise HTTPException(
                status_code=_HTTP_400_BAD_REQUEST,
                detail="lat and lng must be finite numbers when status='ok'",
            )

    async def _claim_and_authorize(self, turn_id: str, account_id: UUID | str) -> PendingTurn:
        """Pending 을 atomic 하게 claim + ownership 검증 — 각각 410/403."""
        store = self._get_pending_store()
        pending = await store.claim(turn_id)
        if pending is None:
            raise HTTPException(
                status_code=_HTTP_410_GONE,
                detail="Pending turn not found or expired.",
            )
        if pending.account_id != str(account_id):
            raise HTTPException(
                status_code=_HTTP_403_FORBIDDEN,
                detail="Access denied to this pending turn.",
            )
        return pending

    async def _collect_tool_results(
        self,
        pending: PendingTurn,
        *,
        status: str,
        lat: float | None,
        lng: float | None,
    ) -> dict[str, Any]:
        """Eager 결과 위에 geo 결과 (or denied) 를 합쳐 최종 results dict 를 만든다."""
        results = dict(pending.eager_results)
        remaining_geo_calls = [
            tc for tc in pending.tool_calls if tc.needs_geolocation and tc.tool_call_id not in results
        ]
        if status == _STATUS_OK:
            if remaining_geo_calls:
                geolocation = {"lat": lat, "lng": lng}
                call_payload = [_tool_call_to_worker_dict(tc, geolocation=geolocation) for tc in remaining_geo_calls]
                geo_results = await run_tool_calls_via_rq(calls=call_payload, queue=self._get_queue())
                results.update(geo_results)
        else:
            for tc in remaining_geo_calls:
                results[tc.tool_call_id] = {"error": _GEOLOCATION_DENIED_MESSAGE}
        return results

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
