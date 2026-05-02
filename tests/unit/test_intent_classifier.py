"""Unit tests for app.services.intent.classifier — 4o-mini IntentClassifier.

PLAN.md §4.1 — IntentClassifier 의 의도된 동작 검증.
Phase 3 [Implement] Green — AsyncOpenAI.beta.chat.completions.parse mock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dtos.intent import IntentClassification, IntentType, SearchFilters
from app.services.intent import classifier as classifier_module
from app.services.intent.classifier import classify_intent

GREETING_MESSAGES = [{"role": "user", "content": "안녕"}]
DOMAIN_QUESTION_MESSAGES = [{"role": "user", "content": "타이레놀 먹어도 돼?"}]
AMBIGUOUS_MESSAGES_NO_HISTORY = [{"role": "user", "content": "그거 부작용은?"}]


def _make_mock_client(parsed: IntentClassification) -> MagicMock:
    """4o-mini parse 응답 mock — 주어진 IntentClassification 반환."""
    client = MagicMock()
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=parsed))]
    client.beta.chat.completions.parse = AsyncMock(return_value=completion)
    return client


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """각 테스트 전 _client / _initialised 초기화."""
    monkeypatch.setattr(classifier_module, "_client", None)
    monkeypatch.setattr(classifier_module, "_initialised", False)


class TestSchemaSanity:
    """IntentClassification Pydantic schema 자체 검증."""

    def test_intent_type_4_members(self) -> None:
        assert {t.value for t in IntentType} == {
            "greeting",
            "out_of_scope",
            "domain_question",
            "ambiguous",
        }

    def test_search_filters_defaults_none(self) -> None:
        f = SearchFilters()
        assert f.target_drug is None
        assert f.target_section is None

    def test_classification_minimal(self) -> None:
        c = IntentClassification(intent=IntentType.GREETING, direct_answer="안녕하세요")
        assert c.intent == IntentType.GREETING
        assert c.fanout_queries is None

    def test_fanout_queries_max_length_10(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=[f"q{i}" for i in range(11)],
            )


class TestClassifyIntent:
    """classify_intent 단위 테스트 (4o-mini mock)."""

    @pytest.mark.asyncio
    async def test_greeting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """'안녕' → intent=greeting, direct_answer 채움."""
        expected = IntentClassification(
            intent=IntentType.GREETING,
            direct_answer="안녕하세요. 무엇을 도와드릴까요?",
        )
        client = _make_mock_client(expected)
        monkeypatch.setattr(classifier_module, "_get_client", lambda: client)

        result = await classify_intent(GREETING_MESSAGES)
        assert result.intent == IntentType.GREETING
        assert result.direct_answer is not None
        assert result.fanout_queries is None

    @pytest.mark.asyncio
    async def test_domain_question_with_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """도메인 질문 + 의학 컨텍스트 → fanout_queries 채움."""
        expected = IntentClassification(
            intent=IntentType.DOMAIN_QUESTION,
            fanout_queries=[
                "타이레놀과 메트포민의 상호작용",
                "타이레놀과 와파린의 상호작용",
                "타이레놀과 오메가3의 상호작용",
                "타이레놀의 일반 부작용",
            ],
            filters=SearchFilters(target_drug="타이레놀"),
        )
        client = _make_mock_client(expected)
        monkeypatch.setattr(classifier_module, "_get_client", lambda: client)

        result = await classify_intent(
            DOMAIN_QUESTION_MESSAGES,
            medical_context="[사용자 의학 컨텍스트]\n- 복용 중인 약: 메트포민, 와파린, 오메가3",
        )
        assert result.intent == IntentType.DOMAIN_QUESTION
        assert result.fanout_queries is not None
        assert len(result.fanout_queries) <= 10
        assert result.direct_answer is None

    @pytest.mark.asyncio
    async def test_ambiguous_no_referent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """history 빈 + 대명사만 → intent=ambiguous + 명확화 질문."""
        expected = IntentClassification(
            intent=IntentType.AMBIGUOUS,
            direct_answer="어느 약에 대한 질문인지 약 이름을 알려주세요.",
        )
        client = _make_mock_client(expected)
        monkeypatch.setattr(classifier_module, "_get_client", lambda: client)

        result = await classify_intent(AMBIGUOUS_MESSAGES_NO_HISTORY)
        assert result.intent == IntentType.AMBIGUOUS
        assert result.direct_answer is not None
        assert "약 이름" in result.direct_answer

    @pytest.mark.asyncio
    async def test_no_api_key_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API key 없을 때 → fallback (intent=ambiguous + 안내 메시지)."""
        monkeypatch.setattr(classifier_module, "_get_client", lambda: None)

        result = await classify_intent(GREETING_MESSAGES)
        assert result.intent == IntentType.AMBIGUOUS
        assert result.direct_answer is not None

    @pytest.mark.asyncio
    async def test_referent_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """history 에 referent 있을 때 → referent_resolution 채움."""
        expected = IntentClassification(
            intent=IntentType.DOMAIN_QUESTION,
            fanout_queries=["타이레놀의 부작용"],
            referent_resolution={"그거": "타이레놀"},
        )
        client = _make_mock_client(expected)
        monkeypatch.setattr(classifier_module, "_get_client", lambda: client)

        messages = [
            {"role": "user", "content": "타이레놀 알려줘"},
            {"role": "assistant", "content": "타이레놀은 ..."},
            {"role": "user", "content": "그거 부작용은?"},
        ]
        result = await classify_intent(messages)
        assert result.referent_resolution == {"그거": "타이레놀"}

    @pytest.mark.asyncio
    async def test_parsed_none_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """4o-mini 가 parsed=None 반환 (극단 케이스) → ambiguous fallback."""
        client = MagicMock()
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(parsed=None))]
        client.beta.chat.completions.parse = AsyncMock(return_value=completion)
        monkeypatch.setattr(classifier_module, "_get_client", lambda: client)

        result = await classify_intent(GREETING_MESSAGES)
        assert result.intent == IntentType.AMBIGUOUS
