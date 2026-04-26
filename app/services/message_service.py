"""Message service module.

This module provides business logic for chat message management operations
including creation, AI response generation, and ownership verification.
"""

from datetime import UTC, datetime
import json
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.tools import AskPending, AskResult, PendingTurn, RouteResult, ToolCall
from app.models.messages import ChatMessage
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import MessageRepository
from app.services.rag import get_rag_pipeline
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


def _preview(text: str, limit: int = 80) -> str:
    """Return a single-line preview of `text` capped at `limit` characters."""
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "..."


def _is_valid_coords(lat: float | None, lng: float | None) -> bool:
    """``lat``/``lng`` 가 유한한 숫자값인지 검증.

    None / NaN / Infinity / 비숫자 모두 거부 — 잘못된 좌표가 ai-worker 까지
    내려가 Kakao API 호출에서 ValueError 로 터지는 것을 callback 진입 단계에서
    명확한 400 으로 끊는다.
    """
    import math

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

    async def ask_and_reply(self, session_id: UUID, content: str) -> tuple[ChatMessage, ChatMessage]:
        """Run RAG pipeline, then persist both turns with their metadata.

        Saving order: user message + assistant message are persisted only AFTER
        the RAG pipeline succeeds so that each row carries the matching
        debug/audit metadata (intent, medicine_names, retrieval scores on the
        user turn; LLM token usage on the assistant turn). If the pipeline
        fails, nothing is persisted.

        Args:
            session_id: Session UUID.
            content: User message content.

        Returns:
            tuple[ChatMessage, ChatMessage]: (user_message, assistant_message)

        Raises:
            HTTPException: If AI response generation fails.
        """
        sid = str(session_id)[:8]
        start = time.perf_counter()
        logger.info("[RAG] session=%s q=%r", sid, _preview(content))

        # Get recent messages (returned in newest-first order). The current
        # user turn is not persisted yet, so it won't appear in `recent`.
        recent = await self.repository.get_recent_by_session(session_id, limit=10)
        chronological = list(reversed(recent))
        history = [
            {"role": "user" if m.sender_type == "USER" else "assistant", "content": m.content} for m in chronological
        ]
        history_metadata = [m.metadata or {} for m in chronological]

        # Resolve the active profile so the RAG pipeline can inject the
        # profile's health_survey (allergies, conditions, etc.) into the
        # answer LLM prompt. A missing session falls through to the pipeline
        # which will simply skip the medical-context block.
        session = await self.session_repository.get_by_id(session_id)
        user_profile_id = session.profile_id if session is not None else None

        try:
            pipeline = await get_rag_pipeline()
            response = await pipeline.ask(
                question=content,
                history=history,
                history_metadata=history_metadata,
                user_profile_id=user_profile_id,
            )
        except Exception as e:
            # 503 으로 변환하기 전에 진짜 원인을 stack trace 와 함께 남긴다.
            # 그렇지 않으면 broad except 가 RAG 파이프라인의 모든 예외를 삼켜
            # 디버깅이 불가능하다. logger.exception 은 traceback 을 자동으로
            # 첨부하므로 메시지에 ``e`` 를 다시 넣지 않는다 (Ruff TRY401).
            logger.exception("[RAG] ask pipeline failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "ai_unavailable",
                    "error_description": "AI response is currently unavailable. Please try again later.",
                    "cause": str(e),
                },
            ) from e

        user_metadata = {
            "intent": response.intent,
            "query_keywords": response.query_keywords,
            "retrieval": response.retrieval.model_dump(),
        }
        assistant_metadata: dict = {"intent": response.intent}
        if response.token_usage is not None:
            assistant_metadata["llm"] = response.token_usage.model_dump()

        user_msg = await self.repository.create_user_message(session_id, content, metadata=user_metadata)
        assistant_msg = await self.repository.create_assistant_message(
            session_id, response.answer, metadata=assistant_metadata
        )

        took_ms = int((time.perf_counter() - start) * 1000)
        usage = response.token_usage
        usage_log = (
            f"tokens={usage.total_tokens}(p{usage.prompt_tokens}+c{usage.completion_tokens})"
            if usage is not None
            else "tokens=?"
        )
        logger.info(
            "[RAG] session=%s reply=%r len=%d %s took=%dms",
            sid,
            _preview(response.answer),
            len(response.answer),
            usage_log,
            took_ms,
        )
        return user_msg, assistant_msg

    async def ask_and_reply_with_owner_check(
        self, session_id: UUID, account_id: UUID, content: str
    ) -> tuple[ChatMessage, ChatMessage]:
        """Save user message, generate RAG-based response with ownership verification.

        Args:
            session_id: Session UUID.
            account_id: Account UUID for ownership check.
            content: User message content.

        Returns:
            tuple[ChatMessage, ChatMessage]: (user_message, assistant_message)

        Raises:
            HTTPException: If session not found, access denied, or AI fails.
        """
        await self._verify_session_ownership(session_id, account_id)
        return await self.ask_and_reply(session_id, content)

    async def ask_with_tools(
        self,
        *,
        session_id: UUID,
        account_id: UUID,
        content: str,
    ) -> AskResult:
        """Route one user turn through the Router LLM and fan out.

        Three branches mirror PLAN.md §8 Y-6:

        - **text** — Router produced a natural-language reply without
          invoking any tool. Fall back to the classic RAG pipeline so
          medical questions keep working unchanged.
        - **tool_calls, all eager** — every tool call can run now
          (keyword-only). Execute in parallel, feed results back to the
          2nd LLM, persist both turns.
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
            HTTPException: Session ownership violations and AI failures
                bubble up unchanged from the RAG fallback path.
        """
        await self._verify_session_ownership(session_id, account_id)

        recent = await self.repository.get_recent_by_session(session_id, limit=_HISTORY_LIMIT)
        history = _chat_messages_to_history(recent)
        route_messages = [*history, {"role": "user", "content": content}]

        queue = self._get_queue()

        route = await route_intent_via_rq(messages=route_messages, queue=queue)
        logger.info("[ToolCalling] route kind=%s calls=%d", route.kind, len(route.tool_calls))

        if route.kind == "text":
            user_msg, assistant_msg = await self.ask_and_reply(session_id, content)
            return AskResult(user_message=user_msg, assistant_message=assistant_msg, pending=None)

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

        Called by the frontend once the user has either allowed or denied
        geolocation access. Validation order is chosen so we never waste
        the (atomic) ``claim`` on a known-bad request:

        1. ``status="ok"`` but missing coords → ``400``.
        2. Turn not in the store (expired / never existed) → ``410``.
        3. Account does not own the turn → ``403``.

        Args:
            turn_id: Id returned to the client as ``AskPending.turn_id``.
            account_id: Caller account id. Compared as a string against
                the owner recorded on the pending turn.
            status: ``"ok"`` (user allowed GPS) or ``"denied"``.
            lat: Latitude (WGS84) when ``status="ok"``.
            lng: Longitude (WGS84) when ``status="ok"``.

        Returns:
            ``AskResult`` with only ``assistant_message`` set — the user
            turn was persisted when the pending was created.

        Raises:
            HTTPException: 400 / 403 / 410 per above.
        """
        if status == _STATUS_OK and not _is_valid_coords(lat, lng):
            raise HTTPException(
                status_code=_HTTP_400_BAD_REQUEST,
                detail="lat and lng must be finite numbers when status='ok'",
            )

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

        results = dict(pending.eager_results)
        remaining_geo_calls = [
            tc for tc in pending.tool_calls if tc.needs_geolocation and tc.tool_call_id not in results
        ]

        if status == _STATUS_OK:
            geolocation = {"lat": lat, "lng": lng}
            if remaining_geo_calls:
                call_payload = [_tool_call_to_worker_dict(tc, geolocation=geolocation) for tc in remaining_geo_calls]
                geo_results = await run_tool_calls_via_rq(calls=call_payload, queue=self._get_queue())
                results.update(geo_results)
        else:
            for tc in remaining_geo_calls:
                results[tc.tool_call_id] = {"error": _GEOLOCATION_DENIED_MESSAGE}

        tool_messages = [_tool_result_message(call_id, result) for call_id, result in results.items()]
        second_messages = [*pending.messages_snapshot, *tool_messages]

        completion = await generate_chat_response_via_rq(
            messages=second_messages,
            system_prompt=None,
            queue=self._get_queue(),
        )
        answer = completion.get("answer", "")

        session_uuid = UUID(pending.session_id)
        assistant_msg = await self.repository.create_assistant_message(session_uuid, answer)
        logger.info("[ToolCalling] resolved turn=%s status=%s", turn_id, status)

        return AskResult(user_message=None, assistant_message=assistant_msg, pending=None)

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
