"""Phase Y-8 — HTTP-level integration tests for the tool-calling flow.

These tests exercise the FastAPI router wiring that Y-7 added on top of
the Y-6 service layer. The service itself is already unit-tested in
``test_message_service_tool_branching.py`` and
``test_message_service_pending_callback.py``; this suite only asserts
what the HTTP transport adds:

- response status code (200 vs 202)
- response body schema + required fields
- ``HTTPException`` propagation from the service (400 / 403 / 410)
- ``get_current_account`` / ``get_message_service`` DI wiring

External boundaries are stubbed at the module-attribute level so no
Redis, no AI-Worker, no OpenAI, no Kakao API calls happen:

- Router LLM  → ``route_intent_via_rq`` stub
- Tool exec   → ``run_tool_calls_via_rq`` stub
- 2nd LLM     → ``generate_chat_response_via_rq`` stub
- RAG fallback → ``MessageService.ask_and_reply`` stub
- DB writes   → ``MessageRepository.create_{user,assistant}_message`` stubs
- Session auth → ``MessageService._verify_session_ownership`` stub

Scenarios mapped to PLAN.md §11:
    Y-8-C/I → keyword-only 200
    Y-8-A   → location 202 + /tool-result allow
    Y-8-B   → /tool-result denied
    Y-8-D/E → RAG fallback 200
    Y-8-F   → expired turn_id 410
    Y-8-G   → account mismatch 403
    (400)   → missing coords on status="ok"
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient
import pytest

from app.apis.v1.message_routers import get_message_service
from app.dependencies.security import get_current_account
from app.dtos.tools import RouteResult, ToolCall
from app.main import app
from app.models.messages import SenderType
from app.repositories.message_repository import MessageRepository
from app.services.message_service import MessageService
from app.services.tools.pending import InMemoryPendingTurnStore


class _StubChatMessage:
    """Tortoise-free stand-in that satisfies ``MessageResponse.model_validate``.

    ``MessageResponse`` uses ``from_attributes=True``, so the router will
    read each field off this object. Values only need to be shape-valid
    (UUID, datetime, SenderType).
    """

    def __init__(self, *, session_id: UUID, content: str, sender_type: SenderType) -> None:
        self.id = uuid4()
        self.session_id = session_id
        self.sender_type = sender_type
        self.content = content
        self.created_at = datetime.now(UTC)
        self.deleted_at: datetime | None = None
        self.metadata: dict[str, Any] = {}


# ── Common fixtures ──────────────────────────────────────────────


@pytest.fixture
def stub_account() -> Any:
    """Minimal ``Account`` stand-in: only ``id`` is consumed by the router."""

    class _Account:
        def __init__(self) -> None:
            self.id = uuid4()

    return _Account()


@pytest.fixture
def pending_store() -> InMemoryPendingTurnStore:
    """Fresh in-memory store per test to avoid cross-test bleed."""
    return InMemoryPendingTurnStore()


@pytest.fixture
def session_id() -> UUID:
    return uuid4()


@pytest.fixture
def override_deps(stub_account: Any, pending_store: InMemoryPendingTurnStore) -> Any:
    """Inject the stub account and a service wired to the shared store.

    Yielding pattern cleans up ``app.dependency_overrides`` so other
    tests keep the real DI graph.
    """
    service = MessageService(pending_store=pending_store, queue=object())

    app.dependency_overrides[get_current_account] = lambda: stub_account
    app.dependency_overrides[get_message_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def stub_repo(monkeypatch: pytest.MonkeyPatch, session_id: UUID) -> dict[str, Any]:
    """Replace DB-touching repository methods with in-memory stubs."""
    captured: dict[str, Any] = {"user": [], "assistant": []}

    async def fake_get_recent(_self, _sid, limit=10) -> list[Any]:  # noqa: ARG001
        return []

    async def fake_user(_self, sid, content, metadata=None) -> _StubChatMessage:
        msg = _StubChatMessage(session_id=session_id, content=content, sender_type=SenderType.USER)
        captured["user"].append((sid, content, metadata))
        return msg

    async def fake_assistant(_self, sid, content, metadata=None) -> _StubChatMessage:
        msg = _StubChatMessage(session_id=session_id, content=content, sender_type=SenderType.ASSISTANT)
        captured["assistant"].append((sid, content, metadata))
        return msg

    monkeypatch.setattr(MessageRepository, "get_recent_by_session", fake_get_recent)
    monkeypatch.setattr(MessageRepository, "create_user_message", fake_user)
    monkeypatch.setattr(MessageRepository, "create_assistant_message", fake_assistant)
    return captured


@pytest.fixture
def stub_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok(_self, _sid, _aid) -> None:
        return

    monkeypatch.setattr(MessageService, "_verify_session_ownership", ok)


# ── POST /messages/ask ──────────────────────────────────────────


class TestAskKeywordOnly:
    """Y-8-C/I — keyword-only tools resolve inside one HTTP request."""

    @pytest.mark.asyncio
    async def test_200_with_both_messages(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
        stub_repo: dict,
        stub_ownership: None,  # noqa: ARG002
        session_id: UUID,
    ) -> None:
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
        route = RouteResult(
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

        async def fake_route(**_: Any) -> RouteResult:
            return route

        async def fake_run(**_: Any) -> dict:
            return {"c1": {"places": [{"place_name": "강남스퀘어약국"}]}}

        async def fake_generate(**_: Any) -> dict:
            return {"answer": "가까운 약국은 강남스퀘어약국입니다.", "token_usage": None}

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", fake_run)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", fake_generate)

        response = await client.post(
            "/api/v1/messages/ask",
            json={"session_id": str(session_id), "content": "강남역 약국"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user_message"]["content"] == "강남역 약국"
        assert body["assistant_message"]["content"] == "가까운 약국은 강남스퀘어약국입니다."
        assert len(stub_repo["user"]) == 1
        assert len(stub_repo["assistant"]) == 1


class TestAskLocationPending:
    """Y-8-A part 1 — location tool yields 202 + pending handoff."""

    @pytest.mark.asyncio
    async def test_202_returns_turn_id_and_ttl(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
        stub_repo: dict,
        stub_ownership: None,  # noqa: ARG002
        session_id: UUID,
        pending_store: InMemoryPendingTurnStore,
    ) -> None:
        route = RouteResult(
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

        async def fake_route(**_: Any) -> RouteResult:
            return route

        async def must_not_run(**_: Any) -> dict:
            raise AssertionError("pending 분기에서 2nd LLM / tool 실행이 일어나면 안 됨")

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", must_not_run)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", must_not_run)

        response = await client.post(
            "/api/v1/messages/ask",
            json={"session_id": str(session_id), "content": "내 주변 약국"},
        )

        assert response.status_code == 202
        body = response.json()
        assert body["action"] == "request_geolocation"
        assert body["session_id"] == str(session_id)
        assert body["ttl_sec"] > 0
        assert body["user_message"]["content"] == "내 주변 약국"

        # pending turn is queryable by the returned id
        assert await pending_store.exists(body["turn_id"])
        assert len(stub_repo["user"]) == 1
        assert len(stub_repo["assistant"]) == 0


class TestAskTextFallback:
    """Y-8-D/E — Router returns text → RAG fallback on 200."""

    @pytest.mark.asyncio
    async def test_200_uses_rag_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
        stub_repo: dict,  # noqa: ARG002
        stub_ownership: None,  # noqa: ARG002
        session_id: UUID,
    ) -> None:
        rag_user = _StubChatMessage(session_id=session_id, content="활명수 효능", sender_type=SenderType.USER)
        rag_assistant = _StubChatMessage(
            session_id=session_id,
            content="활명수는 소화제입니다.",
            sender_type=SenderType.ASSISTANT,
        )

        async def fake_route(**_: Any) -> RouteResult:
            return RouteResult(kind="text", text="안녕하세요", assistant_message={"role": "assistant"})

        async def fake_rag(_self, _sid, _content) -> tuple:
            return rag_user, rag_assistant

        monkeypatch.setattr("app.services.message_service.route_intent_via_rq", fake_route)
        monkeypatch.setattr(MessageService, "ask_and_reply", fake_rag)

        response = await client.post(
            "/api/v1/messages/ask",
            json={"session_id": str(session_id), "content": "활명수 효능"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["user_message"]["content"] == "활명수 효능"
        assert body["assistant_message"]["content"] == "활명수는 소화제입니다."


# ── POST /messages/tool-result ──────────────────────────────────


class TestToolResultAllow:
    """Y-8-A part 2 — GPS allow completes the turn."""

    @pytest.mark.asyncio
    async def test_200_runs_remaining_tools_and_returns_assistant(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: AsyncClient,
        stub_account: Any,
        override_deps: MessageService,  # noqa: ARG002
        stub_repo: dict,
        pending_store: InMemoryPendingTurnStore,
        session_id: UUID,
    ) -> None:
        from app.dtos.tools import PendingTurn

        pending = PendingTurn(
            turn_id="",
            session_id=str(session_id),
            account_id=str(stub_account.id),
            messages_snapshot=[
                {"role": "user", "content": "내 주변 약국"},
                {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
            ],
            tool_calls=[
                ToolCall(
                    tool_call_id="c1",
                    name="search_hospitals_by_location",
                    arguments={"category": "약국"},
                    needs_geolocation=True,
                ),
            ],
            eager_results={},
            created_at=datetime.now(UTC),
        )
        turn_id = await pending_store.create(pending)

        async def fake_run(**kwargs: Any) -> dict:
            calls = kwargs["calls"]
            assert calls[0]["geolocation"] == {"lat": 37.5, "lng": 127.0}
            return {"c1": {"places": [{"place_name": "미진약국"}]}}

        async def fake_generate(**_: Any) -> dict:
            return {"answer": "미진약국이 가깝습니다.", "token_usage": None}

        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", fake_run)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", fake_generate)

        response = await client.post(
            "/api/v1/messages/tool-result",
            json={"turn_id": turn_id, "status": "ok", "lat": 37.5, "lng": 127.0},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["assistant_message"]["content"] == "미진약국이 가깝습니다."
        assert len(stub_repo["assistant"]) == 1
        # 저장된 Pending 은 one-shot claim 으로 사라져야 함
        assert not await pending_store.exists(turn_id)


class TestToolResultDenied:
    """Y-8-B — user denies GPS, LLM gets an error payload."""

    @pytest.mark.asyncio
    async def test_200_without_running_location_tool(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: AsyncClient,
        stub_account: Any,
        override_deps: MessageService,  # noqa: ARG002
        stub_repo: dict,  # noqa: ARG002
        pending_store: InMemoryPendingTurnStore,
        session_id: UUID,
    ) -> None:
        from app.dtos.tools import PendingTurn

        pending = PendingTurn(
            turn_id="",
            session_id=str(session_id),
            account_id=str(stub_account.id),
            messages_snapshot=[
                {"role": "user", "content": "내 주변 약국"},
                {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
            ],
            tool_calls=[
                ToolCall(
                    tool_call_id="c1",
                    name="search_hospitals_by_location",
                    arguments={"category": "약국"},
                    needs_geolocation=True,
                ),
            ],
            eager_results={},
            created_at=datetime.now(UTC),
        )
        turn_id = await pending_store.create(pending)

        async def must_not_run(**_: Any) -> dict:
            raise AssertionError("denied 경로에서 location tool 실행이 일어나면 안 됨")

        captured_messages: dict[str, list] = {}

        async def fake_generate(**kwargs: Any) -> dict:
            captured_messages["messages"] = kwargs["messages"]
            return {"answer": "지역 이름을 알려주시면 찾아드릴게요.", "token_usage": None}

        monkeypatch.setattr("app.services.message_service.run_tool_calls_via_rq", must_not_run)
        monkeypatch.setattr("app.services.message_service.generate_chat_response_via_rq", fake_generate)

        response = await client.post(
            "/api/v1/messages/tool-result",
            json={"turn_id": turn_id, "status": "denied"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["assistant_message"]["content"] == "지역 이름을 알려주시면 찾아드릴게요."

        # LLM 에 전달된 tool 메시지가 denial payload 를 담고 있는지 확인
        tool_msgs = [m for m in captured_messages["messages"] if m.get("role") == "tool"]
        assert tool_msgs
        assert "denied" in tool_msgs[0]["content"].lower()


class TestToolResultErrors:
    """Y-8-F/G + 입력 검증 — HTTPException 전파 경로."""

    @pytest.mark.asyncio
    async def test_unknown_turn_id_returns_410(
        self,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
    ) -> None:
        response = await client.post(
            "/api/v1/messages/tool-result",
            json={"turn_id": str(uuid4()), "status": "ok", "lat": 37.5, "lng": 127.0},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_other_account_turn_id_returns_403(
        self,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
        pending_store: InMemoryPendingTurnStore,
        session_id: UUID,
    ) -> None:
        from app.dtos.tools import PendingTurn

        other_account = str(uuid4())
        pending = PendingTurn(
            turn_id="",
            session_id=str(session_id),
            account_id=other_account,
            messages_snapshot=[],
            tool_calls=[],
            eager_results={},
            created_at=datetime.now(UTC),
        )
        turn_id = await pending_store.create(pending)

        response = await client.post(
            "/api/v1/messages/tool-result",
            json={"turn_id": turn_id, "status": "ok", "lat": 37.5, "lng": 127.0},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_ok_without_coords_returns_400(
        self,
        client: AsyncClient,
        override_deps: MessageService,  # noqa: ARG002
    ) -> None:
        response = await client.post(
            "/api/v1/messages/tool-result",
            json={"turn_id": str(uuid4()), "status": "ok"},
        )
        assert response.status_code == 400
