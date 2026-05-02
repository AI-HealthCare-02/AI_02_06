"""Unit tests for app.services.chat.intent_orchestrator — Step 0 + 1+2 통합."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.dtos.intent import IntentClassification, IntentType
from app.services.chat import intent_orchestrator as orch_module
from app.services.chat.intent_orchestrator import classify_user_turn

SAMPLE_PROFILE_ID: UUID = uuid4()
USER_MESSAGES = [{"role": "user", "content": "타이레놀 먹어도 돼?"}]


class TestClassifyUserTurn:
    """classify_user_turn 통합 helper."""

    @pytest.mark.asyncio
    async def test_passes_medical_context_to_classifier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_medical_context 의 결과가 classify_intent 에 그대로 전달."""
        captured: dict[str, object] = {}

        async def _fake_build(_: UUID) -> str:
            return "[사용자 의학 컨텍스트]\n- 복용 중인 약: 타이레놀"

        async def _fake_classify(messages: list[dict[str, str]], medical_context: str | None = None):
            captured["messages"] = messages
            captured["medical_context"] = medical_context
            return IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=["타이레놀의 부작용"],
            )

        monkeypatch.setattr(orch_module, "build_medical_context", _fake_build)
        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        result = await classify_user_turn(SAMPLE_PROFILE_ID, USER_MESSAGES)
        assert result.intent == IntentType.DOMAIN_QUESTION
        assert captured["messages"] == USER_MESSAGES
        assert "타이레놀" in (captured["medical_context"] or "")

    @pytest.mark.asyncio
    async def test_empty_medical_context_passed_as_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_medical_context 가 빈 문자열 반환 시 classifier 에 None 전달."""
        captured: dict[str, object] = {}

        async def _fake_build(_: UUID) -> str:
            return ""

        async def _fake_classify(messages: list[dict[str, str]], medical_context: str | None = None):
            del messages
            captured["medical_context"] = medical_context
            return IntentClassification(intent=IntentType.GREETING, direct_answer="안녕하세요")

        monkeypatch.setattr(orch_module, "build_medical_context", _fake_build)
        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        await classify_user_turn(SAMPLE_PROFILE_ID, [{"role": "user", "content": "안녕"}])
        assert captured["medical_context"] is None

    @pytest.mark.asyncio
    async def test_returns_classification_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """classifier 가 반환한 IntentClassification 을 그대로 propagate."""
        expected = IntentClassification(
            intent=IntentType.AMBIGUOUS,
            direct_answer="명확화 필요",
        )

        async def _fake_build(_: UUID) -> str:
            return ""

        async def _fake_classify(messages, medical_context=None):  # noqa: ARG001
            return expected

        monkeypatch.setattr(orch_module, "build_medical_context", _fake_build)
        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        result = await classify_user_turn(SAMPLE_PROFILE_ID, USER_MESSAGES)
        assert result is expected
