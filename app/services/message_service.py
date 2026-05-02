"""Message service module.

This module provides business logic for chat message management operations
including creation, AI response generation, and ownership verification.
"""

import json
import logging
import math
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.intent import IntentType
from app.dtos.tools import AskResult, PendingTurn, ToolCall
from app.models.messages import ChatMessage
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import MessageRepository
from app.services.chat.fanout_tool_calls import fanout_to_tool_calls
from app.services.chat.intent_orchestrator import classify_user_turn
from app.services.chat.rag_context_assembler import assemble_rag_section
from app.services.tools.pending import PendingTurnStore
from app.services.tools.rq_adapters import (
    generate_chat_response_via_rq,
    run_tool_calls_via_rq,
)

logger = logging.getLogger(__name__)

# PLAN.md (feature/RAG) §0 결정 — recent history = 6 messages (3 user + 3 assistant).
# 6 turn 마다 chat_sessions.summary 갱신 (옵션 D) 와 정확히 일치 → token 절감.
_HISTORY_LIMIT = 6
_STATUS_OK = "ok"
_STATUS_DENIED = "denied"
_GEOLOCATION_DENIED_MESSAGE = "Permission denied: user rejected geolocation"

# HTTP status codes referenced inside ``resolve_pending_turn`` — the
# ``status`` parameter shadows ``fastapi.status`` in that method, so the
# symbolic aliases are imported up-front to avoid an inline alias.
_HTTP_400_BAD_REQUEST = 400
_HTTP_403_FORBIDDEN = 403
_HTTP_410_GONE = 410

_LOG_PREVIEW_LIMIT = 80

# ── 옵션 D: 세션 요약 자동화 ───────────────────────────────────────
# 매 N turn 마다 background 로 SessionCompactService 호출.
# turn = (user, assistant) 페어 1쌍 ≈ assistant 메시지 1건 기준.
_COMPACT_TRIGGER_EVERY = 6
_COMPACT_TRIGGER_MIN = 6
_COMPACT_JOB_REF = "ai_worker.domains.session_compact.jobs.compact_and_save_session_job"


def _preview(text: str, limit: int = _LOG_PREVIEW_LIMIT) -> str:
    """단일 줄 preview — 로그에서 user/assistant content 를 짧게 보여준다."""
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "..."


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

    # ── RAG 4단 파이프라인 진입점 ────────────────────────────────────────
    # 흐름: ownership -> Step 0 (medical_context) + Step 1+2 (IntentClassifier 4o-mini)
    #       -> direct_answer 분기 (greeting/out_of_scope/ambiguous) 즉시 응답
    #       -> domain_question 이면 Step 3 (fanout → tool_calls 병렬) -> Step 4 (2nd LLM)
    async def ask_with_tools(
        self,
        *,
        session_id: UUID,
        account_id: UUID,
        content: str,
    ) -> AskResult:
        """Route one user turn through the RAG 4-stage pipeline.

        분기:
        - **direct_answer** — IntentClassifier 가 즉시 답변
          (greeting / out_of_scope / ambiguous). Persist 후 종료.
        - **domain_question, all eager** — fanout queries 를 RAG tool_calls
          로 변환 + 병렬 실행 + RAG context inject 후 2nd LLM (4o) 호출.
        - **domain_question, any geo** — (현재 RAG 4단은 GPS tool 안 씀.
          향후 hospital_search 통합 시 PendingTurn 분기 추가 가능).

        Args:
            session_id: Chat session UUID.
            account_id: Caller account UUID (for ownership check).
            content: User message content.

        Returns:
            ``AskResult`` — direct/tool 분기에 따라 다름.

        Raises:
            HTTPException: Session ownership violations.
        """
        sid = str(session_id)[:8]
        logger.info("[Chat] session=%s account=%s q=%r", sid, str(account_id)[:8], _preview(content))

        await self._verify_session_ownership(session_id, account_id)

        # Step 0: history (6 msgs) + summary
        recent = await self.repository.get_recent_by_session(session_id, limit=_HISTORY_LIMIT)
        history = _chat_messages_to_history(recent)
        session_summary = await self._fetch_session_summary(session_id)

        # session.profile_id (Step 0 의 medical_context 입력)
        session_obj = await self.session_repository.get_by_id(session_id)
        if session_obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
        profile_id = session_obj.profile_id

        # ★ user 메시지 영속화 — 실패 시 soft delete rollback
        user_msg = await self.repository.create_user_message(session_id, content)
        try:
            # Step 1+2: medical_context + IntentClassifier (4o-mini)
            classify_messages = [*history, {"role": "user", "content": content}]
            classification = await classify_user_turn(profile_id, classify_messages)

            # 분기 1: direct_answer — IntentClassifier 가 즉시 답변
            if classification.direct_answer:
                logger.info(
                    "[Chat] session=%s intent=%s direct_answer (no RAG)",
                    sid,
                    classification.intent.value,
                )
                return await self._persist_direct_answer_turn(session_id, user_msg, classification.direct_answer)

            # 분기 2: domain_question — fan-out → RAG tool_calls 병렬
            if classification.intent != IntentType.DOMAIN_QUESTION or not classification.fanout_queries:
                # 안전망: domain_question 인데 fanout 비어있는 케이스 (4o-mini 가 어김)
                logger.warning(
                    "[Chat] session=%s domain_question but no fanout_queries — fallback message",
                    sid,
                )
                fallback = "어떤 약이나 증상에 대해 알려드릴까요? 좀 더 구체적으로 말씀해주세요."
                return await self._persist_direct_answer_turn(session_id, user_msg, fallback)

            tool_calls = fanout_to_tool_calls(classification)
            logger.info(
                "[Chat] session=%s fanout=%d queries → %d tool_calls",
                sid,
                len(classification.fanout_queries),
                len(tool_calls),
            )

            # Step 3: tool_calls 병렬 실행 (ai_worker.run_tool_calls_job)
            queue = self._get_queue()
            payload = [_tool_call_to_worker_dict(tc) for tc in tool_calls]
            tool_results = await run_tool_calls_via_rq(calls=payload, queue=queue)

            # Step 4: RAG context inject + 2nd LLM
            return await self._finalize_rag_turn(
                session_id=session_id,
                user_msg=user_msg,
                history=history,
                session_summary=session_summary,
                content=content,
                tool_calls=tool_calls,
                tool_results=tool_results,
                classification=classification,
            )
        except Exception:
            await self.repository.soft_delete(user_msg)
            logger.exception("[Chat] session=%s server error — rolled back user msg", sid)
            raise

    async def _fetch_session_summary(self, session_id: UUID) -> str | None:
        """chat_sessions.summary 조회 — 옵션 D 의 history prepend 입력."""
        session = await self.session_repository.get_by_id(session_id)
        return session.summary if session is not None else None

    def _maybe_enqueue_compact(self, session_id: UUID, total_messages_after: int) -> None:
        """N turn 마다 compact RQ job 을 fire-and-forget enqueue.

        - assistant 메시지 1건 = 1 turn 기준이라 보고, total_messages_after 가
          (user+assistant) 짝수일 때만 trigger 검토.
        - 최소 _COMPACT_TRIGGER_MIN 이상 + _COMPACT_TRIGGER_EVERY 의 배수일 때 실행.
        """
        if total_messages_after < _COMPACT_TRIGGER_MIN:
            return
        if total_messages_after % _COMPACT_TRIGGER_EVERY != 0:
            return
        try:
            self._get_queue().enqueue(_COMPACT_JOB_REF, str(session_id))
            logger.info(
                "[Chat] session=%s compact enqueued (msgs=%d)",
                str(session_id)[:8],
                total_messages_after,
            )
        except Exception:
            # fire-and-forget — enqueue 실패는 사용자 응답을 막지 않는다.
            logger.exception("[Chat] session=%s compact enqueue failed", str(session_id)[:8])

    async def _persist_direct_answer_turn(
        self,
        session_id: UUID,
        user_msg: ChatMessage,
        text: str,
    ) -> AskResult:
        """IntentClassifier 가 직접 답변한 turn — assistant 만 persist."""
        logger.info(
            "[Chat] session=%s direct_answer reply=%r len=%d",
            str(session_id)[:8],
            _preview(text),
            len(text),
        )
        assistant_msg = await self.repository.create_assistant_message(session_id, text)
        total = await self.repository.count_by_session(session_id)
        self._maybe_enqueue_compact(session_id, total)
        return AskResult(user_message=user_msg, assistant_message=assistant_msg, pending=None)

    async def _finalize_rag_turn(
        self,
        *,
        session_id: UUID,
        user_msg: ChatMessage,
        history: list[dict[str, str]],
        session_summary: str | None,
        content: str,
        tool_calls: list[ToolCall],
        tool_results: dict[str, Any],
        classification: Any,
    ) -> AskResult:
        """RAG retrieval 결과를 system prompt 에 inject 한 후 2nd LLM 호출.

        2nd LLM 의 messages 구조 (PLAN.md §2.3 / RAG_FLOW.md §2.4):
          - system: persona + output rule + [세션 요약] + [명확화] + [검색된 약품 정보]
          - history (3 user + 3 assistant)
          - user (현재 turn raw query)
          - assistant tool_calls + tool results (OpenAI 표준 페어링)
        """
        del tool_calls  # 현재는 OpenAI tool_call 페어링 불필요 (RAG 결과는 system 에 inject)

        rag_section = assemble_rag_section(tool_results)
        system_prompt = _compose_system_prompt(
            session_summary=session_summary,
            referent_resolution=classification.referent_resolution,
            rag_section=rag_section,
        )
        second_messages = [
            *history,
            {"role": "user", "content": content},
        ]
        # ── 진단 로그 (diag/2nd-llm-input-output-logging) ───────────────
        # 흐름: 2nd LLM enqueue 직전 system_prompt 전체 + messages 구조 dump
        logger.info(
            "[Chat-Diag] session=%s system_prompt[%dchars]=%r second_messages=%d "
            "rag_section[%dchars]=%r referent_resolution=%s",
            str(session_id)[:8],
            len(system_prompt),
            system_prompt,
            len(second_messages),
            len(rag_section),
            rag_section,
            classification.referent_resolution,
        )
        completion = await generate_chat_response_via_rq(
            messages=second_messages,
            system_prompt=system_prompt,
            queue=self._get_queue(),
        )
        answer = completion.get("answer", "")
        logger.info(
            "[Chat] session=%s rag_finalize tools=%d chunks_inject=%dchars reply=%r len=%d",
            str(session_id)[:8],
            len(tool_results),
            len(rag_section),
            _preview(answer),
            len(answer),
        )

        assistant_msg = await self.repository.create_assistant_message(session_id, answer)
        total = await self.repository.count_by_session(session_id)
        self._maybe_enqueue_compact(session_id, total)
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
        total = await self.repository.count_by_session(session_uuid)
        self._maybe_enqueue_compact(session_uuid, total)
        logger.info(
            "[Chat] resolved turn=%s session=%s status=%s tools=%d reply=%r len=%d",
            turn_id,
            str(session_uuid)[:8],
            status,
            len(results),
            _preview(answer),
            len(answer),
        )
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


# ── 2nd LLM system prompt 조립 ──────────────────────────────────────
# RAG_FLOW.md §2.4 의 권장 섹션 순서:
#   1. persona  2. output rule  3. (의학 컨텍스트는 IntentClassifier 가 흡수)
#   4. 세션 요약  5. 명확화 (referent_resolution 있을 때)  6. RAG 검색 결과
_PERSONA_AND_RULES = (
    "당신은 'Dayak' 약사 챗봇입니다. 따뜻하고 친근한 어조 (해요체) 로 응답합니다.\n"
    "출력 규칙:\n"
    "- 한국어 GFM. 코드 블록 금지.\n"
    "- 답변 안에서 [약: 약품명] [section] 형식으로 출처 인라인 명시.\n"
    "- 의학적 진단/처방 변경 제안 금지. 의사·약사 상담 권고.\n"
    "- 약물 상호작용·부작용·금기 정보가 검색 결과에 있으면 적극 반영."
)


def _compose_system_prompt(
    *,
    session_summary: str | None,
    referent_resolution: dict[str, str] | None,
    rag_section: str,
) -> str:
    """2nd LLM (4o) 의 system prompt 를 6 섹션 순서로 조립한다."""
    parts: list[str] = [_PERSONA_AND_RULES]

    if session_summary:
        parts.append(f"[세션 요약]\n{session_summary}")

    if referent_resolution:
        clarif_lines = "\n".join(f"- '{k}' → '{v}'" for k, v in referent_resolution.items())
        parts.append(f"[명확화]\n{clarif_lines}")

    if rag_section:
        # rag_section 에 이미 [검색된 약품 정보] 헤더 포함
        parts.append(rag_section)

    return "\n\n".join(parts)
