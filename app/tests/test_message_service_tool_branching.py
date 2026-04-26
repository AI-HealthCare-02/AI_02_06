"""MessageService.ask_with_tools 분기 동작 테스트 (Y-6 Red).

세 분기 각각을 독립 검증:
A. Router → text  → RAG 폴백 → AskResult(user, assistant, pending=None)
B. Router → tool_calls (keyword only) → 병렬 실행 → 2nd LLM → AskResult(user, assistant, None)
C. Router → tool_calls (location 포함) → user_msg 저장 + PendingTurn.create
   → AskResult(user, assistant=None, pending=AskPending(turn_id, ttl_sec))

외부 의존성 (Router LLM / run_tool_calls / 2nd LLM / PendingTurnStore /
RAG pipeline) 은 모두 monkeypatch 로 대체해 service 로직만 검증한다.
"""

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.dtos.tools import (
    AskPending,
    AskResult,
    PendingTurn,
    RouteResult,
    ToolCall,
)
from app.services.message_service import MessageService
from app.services.tools.pending import InMemoryPendingTurnStore

# ── 공통 세션/메시지 레포 mock ─────────────────────────────────


class _StubChatMessage:
    """기존 ChatMessage 를 흉내내는 간단한 스텁."""

    def __init__(self, *, message_id: str, content: str, sender_type: str) -> None:
        self.id = message_id
        self.content = content
        self.sender_type = sender_type
        self.metadata: dict[str, Any] = {}


@pytest.fixture
def stub_session_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok(_self, _sid, _aid) -> None:
        return

    monkeypatch.setattr(MessageService, "_verify_session_ownership", ok)


@pytest.fixture
def stub_message_repo(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {"user": [], "assistant": [], "recent": []}

    async def fake_get_recent(_self, _sid, limit=10) -> list[Any]:  # noqa: ARG001
        return captured["recent"]

    async def fake_user(_self, sid, content, metadata=None) -> _StubChatMessage:
        msg = _StubChatMessage(message_id=str(uuid4()), content=content, sender_type="USER")
        msg.metadata = metadata or {}
        captured["user"].append((sid, content, metadata))
        return msg

    async def fake_assistant(_self, sid, content, metadata=None) -> _StubChatMessage:
        msg = _StubChatMessage(message_id=str(uuid4()), content=content, sender_type="ASSISTANT")
        msg.metadata = metadata or {}
        captured["assistant"].append((sid, content, metadata))
        return msg

    from app.repositories.message_repository import MessageRepository

    monkeypatch.setattr(MessageRepository, "get_recent_by_session", fake_get_recent)
    monkeypatch.setattr(MessageRepository, "create_user_message", fake_user)
    monkeypatch.setattr(MessageRepository, "create_assistant_message", fake_assistant)

    return captured


# ── A. Router → text → RAG 폴백 ────────────────────────────────


class TestRagFallbackBranch:
    @pytest.mark.asyncio
    async def test_text_route_falls_back_to_ask_and_reply(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_session_ownership: None,  # noqa: ARG002
        stub_message_repo: dict,  # noqa: ARG002
    ) -> None:
        session_id = uuid4()
        account_id = uuid4()

        async def fake_route(*_, **__) -> RouteResult:
            return RouteResult(kind="text", text="안녕하세요", assistant_message={"role": "assistant"})

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)

        legacy_user = _StubChatMessage(message_id="u", content="안녕", sender_type="USER")
        legacy_assistant = _StubChatMessage(message_id="a", content="RAG 답변", sender_type="ASSISTANT")

        async def fake_legacy_ask(self, sid, content):  # noqa: ARG001
            return legacy_user, legacy_assistant

        monkeypatch.setattr(MessageService, "ask_and_reply", fake_legacy_ask)

        service = MessageService()
        result = await service.ask_with_tools(session_id=session_id, account_id=account_id, content="안녕")

        assert isinstance(result, AskResult)
        assert result.user_message is legacy_user
        assert result.assistant_message is legacy_assistant
        assert result.pending is None


# ── B. Router → keyword-only tool_calls → 즉시 실행 ───────────


class TestKeywordOnlyBranch:
    @pytest.mark.asyncio
    async def test_single_keyword_tool_runs_and_continues_llm(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_session_ownership: None,  # noqa: ARG002
        stub_message_repo: dict,
    ) -> None:
        session_id = uuid4()
        account_id = uuid4()

        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "search_hospitals_by_keyword", "arguments": '{"query": "강남역 약국"}'},
                },
            ],
        }
        route_result = RouteResult(
            kind="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_call_id="c1",
                    name="search_hospitals_by_keyword",
                    arguments={"query": "강남역 약국"},
                    needs_geolocation=False,
                ),
            ],
            assistant_message=assistant_message,
        )

        async def fake_route(*_, **__) -> RouteResult:
            return route_result

        async def fake_run_tool_calls(*, calls, queue, **_) -> dict:  # noqa: ARG001
            assert len(calls) == 1
            return {"c1": {"places": [{"place_name": "강남스퀘어약국"}]}}

        async def fake_generate(*, messages, system_prompt=None, queue) -> dict:  # noqa: ARG001
            # 2nd LLM 에 전달되는 messages 에 assistant_message 와 tool role 결과가 모두 있어야 함
            roles = [m.get("role") for m in messages]
            assert "assistant" in roles
            assert "tool" in roles
            return {"answer": "가까운 약국은 강남스퀘어약국입니다.", "token_usage": None}

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", fake_run_tool_calls)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", fake_generate)

        service = MessageService()
        result = await service.ask_with_tools(session_id=session_id, account_id=account_id, content="강남역 약국")

        assert result.pending is None
        assert result.user_message is not None
        assert result.assistant_message is not None
        assert result.assistant_message.content == "가까운 약국은 강남스퀘어약국입니다."
        # user_msg 와 assistant_msg 둘 다 저장됨
        assert len(stub_message_repo["user"]) == 1
        assert len(stub_message_repo["assistant"]) == 1


# ── C. Router → location 포함 → PendingTurn ──────────────────


class TestLocationPendingBranch:
    @pytest.mark.asyncio
    async def test_location_tool_creates_pending_turn(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_session_ownership: None,  # noqa: ARG002
        stub_message_repo: dict,
    ) -> None:
        session_id = uuid4()
        account_id = uuid4()

        route_result = RouteResult(
            kind="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_call_id="c1",
                    name="search_hospitals_by_location",
                    arguments={"category": "약국"},
                    needs_geolocation=True,
                ),
            ],
            assistant_message={"role": "assistant", "content": None, "tool_calls": [...]},
        )

        async def fake_route(*_, **__) -> RouteResult:
            return route_result

        async def should_not_run_llm(**_: Any) -> dict:
            raise AssertionError("location 분기에서 2nd LLM 미리 호출되면 안 됨")

        async def should_not_run_tool(**_: Any) -> dict:
            raise AssertionError("location 분기에서 run_tool_calls 미리 호출되면 안 됨")

        store = InMemoryPendingTurnStore()

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", should_not_run_tool)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", should_not_run_llm)

        service = MessageService(pending_store=store)
        result = await service.ask_with_tools(
            session_id=session_id,
            account_id=account_id,
            content="내 주변 약국",
        )

        assert result.pending is not None
        assert isinstance(result.pending, AskPending)
        assert result.pending.turn_id
        assert result.pending.ttl_sec > 0
        assert result.assistant_message is None
        # user_msg 저장됨
        assert len(stub_message_repo["user"]) == 1
        # PendingTurn 이 store 에 살아있음
        assert await store.exists(result.pending.turn_id)

    @pytest.mark.asyncio
    async def test_keyword_and_location_mix_saves_eager_results(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_session_ownership: None,  # noqa: ARG002
        stub_message_repo: dict,  # noqa: ARG002
    ) -> None:
        """keyword + location 혼합: keyword 는 즉시 실행 후 PendingTurn.eager_results 에 캐시."""
        session_id = uuid4()
        account_id = uuid4()

        route_result = RouteResult(
            kind="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_call_id="c1",
                    name="search_hospitals_by_keyword",
                    arguments={"query": "강남역 약국"},
                    needs_geolocation=False,
                ),
                ToolCall(
                    tool_call_id="c2",
                    name="search_hospitals_by_location",
                    arguments={"category": "병원"},
                    needs_geolocation=True,
                ),
            ],
            assistant_message={"role": "assistant"},
        )

        async def fake_route(*_, **__) -> RouteResult:
            return route_result

        eager_capture: dict[str, Any] = {}

        async def fake_run_tool_calls(*, calls, queue, **_) -> dict:  # noqa: ARG001
            # keyword 만 넘어와야 함
            assert len(calls) == 1
            assert calls[0]["name"] == "search_hospitals_by_keyword"
            result = {"c1": {"places": [{"place_name": "강남스퀘어약국"}]}}
            eager_capture["result"] = result
            return result

        store = InMemoryPendingTurnStore()

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", fake_run_tool_calls)
        monkeypatch.setattr(
            "app.services.message_service.generate_chat_response_via_rq",
            AsyncMock(side_effect=AssertionError("mix 분기에서 2nd LLM 미리 호출되면 안 됨")),
        )

        service = MessageService(pending_store=store)
        result = await service.ask_with_tools(
            session_id=session_id,
            account_id=account_id,
            content="강남역 약국이랑 내 주변 병원",
        )

        assert result.pending is not None
        # PendingTurn 에 eager_results 가 저장되어 있어야 함
        pending: PendingTurn | None = await store.claim(result.pending.turn_id)
        assert pending is not None
        assert "c1" in pending.eager_results
        assert pending.eager_results["c1"]["places"][0]["place_name"] == "강남스퀘어약국"
