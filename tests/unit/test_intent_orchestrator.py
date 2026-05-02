"""Unit tests for app.services.chat.intent_orchestrator — Step 0 + 1+2 통합."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.dtos.intent import IntentClassification, IntentType
from app.services.chat import intent_orchestrator as orch_module
from app.services.chat.intent_orchestrator import classify_user_turn

SAMPLE_PROFILE_ID: UUID = uuid4()
USER_MESSAGES = [{"role": "user", "content": "타이레놀 먹어도 돼?"}]


@pytest.fixture
def _stub_dependencies(monkeypatch: pytest.MonkeyPatch):
    """build_medical_context / map_brands / _load_medication_names / classify_intent 기본 stub."""

    async def _fake_build(_: UUID) -> str:
        return "[사용자 의학 컨텍스트]\n- 복용 중인 약: 타이레놀, 메트포민"

    async def _fake_load_meds(_: UUID) -> list[str]:
        return ["타이레놀", "메트포민"]

    async def _fake_map(_brands: list[str]) -> dict[str, list[str]]:
        return {"타이레놀": ["아세트아미노펜"], "메트포민": ["메트포르민염산염"]}

    monkeypatch.setattr(orch_module, "build_medical_context", _fake_build)
    monkeypatch.setattr(orch_module, "_load_medication_names", _fake_load_meds)
    monkeypatch.setattr(orch_module, "map_brands_to_ingredients", _fake_map)
    return monkeypatch


class TestClassifyUserTurn:
    """classify_user_turn 통합 helper - tuple 반환."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_stub_dependencies")
    async def test_returns_three_tuple_with_mapping(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """(medical_context, ingredient_mapping_section, classification) 3-tuple 반환."""
        captured: dict[str, object] = {}

        async def _fake_classify(_messages: list[dict[str, str]], medical_context: str | None = None):
            captured["medical_context"] = medical_context
            return IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=["아세트아미노펜과 메트포르민염산염의 상호작용"],
            )

        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        medical_context, mapping_section, classification = await classify_user_turn(
            SAMPLE_PROFILE_ID,
            USER_MESSAGES,
        )

        # medical_context 정상 반환
        assert "타이레놀" in medical_context
        # 매핑 섹션 정상 조립 (헤더 + brand→성분)
        assert "[용어 매핑]" in mapping_section
        assert "타이레놀 → 성분: 아세트아미노펜" in mapping_section
        assert "메트포민 → 성분: 메트포르민염산염" in mapping_section
        # classifier 에 medical_context + mapping 합쳐 전달
        passed = captured["medical_context"]
        assert passed is not None
        assert "타이레놀" in passed
        assert "[용어 매핑]" in passed
        # classification propagate
        assert classification.intent == IntentType.DOMAIN_QUESTION

    @pytest.mark.asyncio
    async def test_empty_context_and_no_medications(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """medical_context 빈 문자열 + medications 0개 → classifier 에 None 전달, mapping 빈 문자열."""

        async def _fake_build(_: UUID) -> str:
            return ""

        async def _fake_load_meds(_: UUID) -> list[str]:
            return []

        async def _fake_map(_: list[str]) -> dict[str, list[str]]:
            return {}

        captured: dict[str, object] = {}

        async def _fake_classify(messages, medical_context=None):  # noqa: ARG001
            captured["medical_context"] = medical_context
            return IntentClassification(intent=IntentType.GREETING, direct_answer="안녕하세요")

        monkeypatch.setattr(orch_module, "build_medical_context", _fake_build)
        monkeypatch.setattr(orch_module, "_load_medication_names", _fake_load_meds)
        monkeypatch.setattr(orch_module, "map_brands_to_ingredients", _fake_map)
        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        medical_context, mapping_section, classification = await classify_user_turn(
            SAMPLE_PROFILE_ID,
            [{"role": "user", "content": "안녕"}],
        )

        assert medical_context == ""
        assert mapping_section == ""
        assert captured["medical_context"] is None
        assert classification.intent == IntentType.GREETING

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_stub_dependencies")
    async def test_propagates_classification_unchanged(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """classifier 가 반환한 IntentClassification 을 그대로 propagate."""
        expected = IntentClassification(
            intent=IntentType.AMBIGUOUS,
            direct_answer="명확화 필요",
        )

        async def _fake_classify(messages, medical_context=None):  # noqa: ARG001
            return expected

        monkeypatch.setattr(orch_module, "classify_intent", _fake_classify)

        _, _, classification = await classify_user_turn(SAMPLE_PROFILE_ID, USER_MESSAGES)
        assert classification is expected
