"""e2e mock 통합 테스트 — MessageService.ask_with_tools 4단 파이프라인.

PLAN.md (feature/RAG) §6 Step 6 — 5-1 시나리오 ("타이레놀 먹어도 돼?").
실 OpenAI / DB 호출은 모두 mock. 흐름 자체의 정합성만 검증.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.dtos.intent import IntentClassification, IntentType, SearchFilters
from app.services import message_service as ms_module

SESSION_ID = uuid4()
ACCOUNT_ID = uuid4()
PROFILE_ID = uuid4()


def _stub_chat_session(profile_id: UUID, account_id: UUID) -> MagicMock:
    session = MagicMock()
    session.id = SESSION_ID
    session.profile_id = profile_id
    session.account_id = account_id
    session.summary = None
    return session


def _stub_user_message(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.id = uuid4()
    return msg


def _stub_assistant_message(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.id = uuid4()
    return msg


@pytest.fixture
def service() -> ms_module.MessageService:
    """MessageService 인스턴스 — repository / session_repository / queue mock."""
    svc = ms_module.MessageService(queue=MagicMock())

    # session_repository 의 get_by_id → stub session
    svc.session_repository = MagicMock()
    svc.session_repository.get_by_id = AsyncMock(return_value=_stub_chat_session(PROFILE_ID, ACCOUNT_ID))

    # repository 의 user/assistant 메시지 생성 + recent + count
    svc.repository = MagicMock()
    svc.repository.get_recent_by_session = AsyncMock(return_value=[])
    svc.repository.create_user_message = AsyncMock(side_effect=lambda _sid, content: _stub_user_message(content))
    svc.repository.create_assistant_message = AsyncMock(
        side_effect=lambda _sid, content: _stub_assistant_message(content)
    )
    svc.repository.count_by_session = AsyncMock(return_value=2)
    svc.repository.soft_delete = AsyncMock()
    return svc


class TestAskWithToolsDirectAnswer:
    """Step 1+2 의 direct_answer 분기 — RAG retrieval 없이 즉시 답변."""

    @pytest.mark.asyncio
    async def test_greeting_returns_direct_answer(
        self,
        service: ms_module.MessageService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """'안녕' → IntentClassifier 가 greeting + direct_answer → 2nd LLM 호출 X."""

        async def _fake_classify(_pid: UUID, _msgs: list[dict[str, str]]) -> IntentClassification:
            return IntentClassification(
                intent=IntentType.GREETING,
                direct_answer="안녕하세요. 무엇을 도와드릴까요?",
            )

        run_tool_calls_mock = AsyncMock()
        generate_mock = AsyncMock()
        monkeypatch.setattr(ms_module, "classify_user_turn", _fake_classify)
        monkeypatch.setattr(ms_module, "run_tool_calls_via_rq", run_tool_calls_mock)
        monkeypatch.setattr(ms_module, "generate_chat_response_via_rq", generate_mock)

        result = await service.ask_with_tools(
            session_id=SESSION_ID,
            account_id=ACCOUNT_ID,
            content="안녕",
        )

        assert result.assistant_message is not None
        assert result.assistant_message.content == "안녕하세요. 무엇을 도와드릴까요?"
        assert result.pending is None
        # direct_answer 분기 → tool_calls / 2nd LLM 모두 호출 X
        run_tool_calls_mock.assert_not_called()
        generate_mock.assert_not_called()


class TestAskWithToolsDomainQuestion:
    """5-1 시나리오 핵심 — 'domain_question' 분기 (fanout → tool_calls → 2nd LLM)."""

    @pytest.mark.asyncio
    async def test_tylenol_question_full_pipeline(
        self,
        service: ms_module.MessageService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """'타이레놀 먹어도 돼?' → fan-out → 5 tool_calls → RAG context inject → 2nd LLM."""

        async def _fake_classify(_pid: UUID, _msgs: list[dict[str, str]]) -> IntentClassification:
            return IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=[
                    "타이레놀과 메트포민의 상호작용",
                    "타이레놀과 와파린의 상호작용",
                    "타이레놀과 오메가3의 상호작용",
                    "타이레놀의 페니실린 알레르기 가능성",
                    "타이레놀의 일반 부작용 및 주의사항",
                ],
                referent_resolution=None,
                filters=SearchFilters(target_drug="타이레놀"),
            )

        captured_tool_calls: dict[str, Any] = {}

        async def _fake_run_tool_calls(*, calls: list[dict], queue: Any) -> dict[str, Any]:
            del queue
            captured_tool_calls["calls"] = calls
            # 각 fan-out call 마다 chunk 1개 반환 (mock RAG retrieval)
            return {
                call["tool_call_id"]: {
                    "chunks": [
                        {
                            "medicine_name": "타이레놀",
                            "section": "drug_interaction",
                            "content": f"타이레놀 chunk for {call['arguments']['query']}",
                            "score": 0.9,
                        },
                    ],
                }
                for call in calls
            }

        captured_2nd_llm: dict[str, Any] = {}

        async def _fake_generate(
            *, messages: list[dict[str, str]], system_prompt: str | None, queue: Any
        ) -> dict[str, Any]:
            del queue
            captured_2nd_llm["messages"] = messages
            captured_2nd_llm["system_prompt"] = system_prompt
            return {
                "answer": "타이레놀은 와파린과 함께 복용 시 INR 상승으로 출혈 위험이 있어요.",
                "token_usage": None,
            }

        monkeypatch.setattr(ms_module, "classify_user_turn", _fake_classify)
        monkeypatch.setattr(ms_module, "run_tool_calls_via_rq", _fake_run_tool_calls)
        monkeypatch.setattr(ms_module, "generate_chat_response_via_rq", _fake_generate)

        result = await service.ask_with_tools(
            session_id=SESSION_ID,
            account_id=ACCOUNT_ID,
            content="타이레놀 먹어도 돼?",
        )

        # 1. fan-out 5 → tool_calls 5
        assert len(captured_tool_calls["calls"]) == 5
        assert all(c["name"] == "search_medicine_knowledge_base" for c in captured_tool_calls["calls"])

        # 2. 2nd LLM 의 system_prompt 에 RAG context inject 됨
        sp = captured_2nd_llm["system_prompt"]
        assert "[검색된 약품 정보]" in sp
        assert "타이레놀" in sp

        # 3. 2nd LLM 의 messages 에 user 마지막 turn (raw query) 포함
        msgs = captured_2nd_llm["messages"]
        assert any(m["role"] == "user" and m["content"] == "타이레놀 먹어도 돼?" for m in msgs)

        # 4. assistant 응답 persist
        assert result.assistant_message is not None
        assert "와파린" in result.assistant_message.content

    @pytest.mark.asyncio
    async def test_referent_resolution_injected_to_clarification(
        self,
        service: ms_module.MessageService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """referent_resolution 가 있으면 system_prompt 의 [명확화] 섹션에 inject."""

        async def _fake_classify(_pid: UUID, _msgs: list[dict[str, str]]) -> IntentClassification:
            return IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=["타이레놀의 부작용"],
                referent_resolution={"그거": "타이레놀"},
            )

        async def _fake_run_tool_calls(*, calls: list[dict], queue: Any) -> dict[str, Any]:
            del queue
            return {
                calls[0]["tool_call_id"]: {
                    "chunks": [
                        {
                            "medicine_name": "타이레놀",
                            "section": "adverse_reaction",
                            "content": "흔한 부작용",
                            "score": 0.9,
                        },
                    ],
                }
            }

        captured: dict[str, Any] = {}

        async def _fake_generate(
            *, messages: list[dict[str, str]], system_prompt: str | None, queue: Any
        ) -> dict[str, Any]:
            del messages, queue
            captured["system_prompt"] = system_prompt
            return {"answer": "타이레놀은 ...", "token_usage": None}

        monkeypatch.setattr(ms_module, "classify_user_turn", _fake_classify)
        monkeypatch.setattr(ms_module, "run_tool_calls_via_rq", _fake_run_tool_calls)
        monkeypatch.setattr(ms_module, "generate_chat_response_via_rq", _fake_generate)

        await service.ask_with_tools(
            session_id=SESSION_ID,
            account_id=ACCOUNT_ID,
            content="그거 부작용은?",
        )

        sp = captured["system_prompt"]
        assert "[명확화]" in sp
        assert "'그거' → '타이레놀'" in sp

    @pytest.mark.asyncio
    async def test_domain_question_without_fanout_fallback(
        self,
        service: ms_module.MessageService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """안전망: domain_question 인데 fanout 비어있으면 fallback message."""

        async def _fake_classify(_pid: UUID, _msgs: list[dict[str, str]]) -> IntentClassification:
            return IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=None,  # 4o-mini 가 어긴 케이스
            )

        run_tool_calls_mock = AsyncMock()
        generate_mock = AsyncMock()
        monkeypatch.setattr(ms_module, "classify_user_turn", _fake_classify)
        monkeypatch.setattr(ms_module, "run_tool_calls_via_rq", run_tool_calls_mock)
        monkeypatch.setattr(ms_module, "generate_chat_response_via_rq", generate_mock)

        result = await service.ask_with_tools(
            session_id=SESSION_ID,
            account_id=ACCOUNT_ID,
            content="약 먹어도 돼?",
        )

        assert result.assistant_message is not None
        # fallback 안내 메시지
        assert "구체적" in result.assistant_message.content
        run_tool_calls_mock.assert_not_called()
        generate_mock.assert_not_called()


class TestAskWithToolsRollback:
    """예외 발생 시 user 메시지 soft_delete 검증."""

    @pytest.mark.asyncio
    async def test_classify_failure_rolls_back_user_msg(
        self,
        service: ms_module.MessageService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """classify_user_turn 이 예외 던지면 user_msg soft_delete 호출 + 예외 propagate."""

        async def _fake_classify(_pid: UUID, _msgs: list[dict[str, str]]) -> IntentClassification:
            raise RuntimeError("4o-mini API down")

        monkeypatch.setattr(ms_module, "classify_user_turn", _fake_classify)

        with pytest.raises(RuntimeError, match="4o-mini API down"):
            await service.ask_with_tools(
                session_id=SESSION_ID,
                account_id=ACCOUNT_ID,
                content="타이레놀",
            )

        service.repository.soft_delete.assert_awaited_once()
