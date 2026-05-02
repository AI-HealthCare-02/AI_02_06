"""Unit tests for app.services.intent.classifier — 4o-mini IntentClassifier.

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 AsyncOpenAI mock 으로 Structured Outputs 검증.

PLAN.md §4.1 — IntentClassifier 의 6가지 의도된 동작:
- '안녕' → intent=greeting, direct_answer 채움, fanout_queries=None
- '타이레놀 먹어도 돼?' + 컨텍스트(복용약 3 + 기저질환 2 + 알레르기 1)
  → intent=domain_question, fanout_queries 7개 이내 (음성응답 제외)
- 만성질환자 컨텍스트 (복용약 12 + 기저질환 5 + 알레르기 2)
  → fanout_queries 정확히 10개 (cap), 우선순위 순
- is_smoking=False 등 음성응답은 query 안 만듦
- '그거 부작용은?' (history 의 '타이레놀' referent 추출 가능)
  → referent_resolution={'그거': '타이레놀'} 채움
- '그거 부작용은?' (history 빈 / referent 없음)
  → intent=ambiguous, direct_answer 명확화 질문
"""

from __future__ import annotations

import pytest

from app.dtos.intent import IntentClassification, IntentType, SearchFilters
from app.services.intent.classifier import classify_intent

GREETING_MESSAGES = [{"role": "user", "content": "안녕"}]

DOMAIN_QUESTION_MESSAGES = [{"role": "user", "content": "타이레놀 먹어도 돼?"}]

AMBIGUOUS_MESSAGES_NO_HISTORY = [{"role": "user", "content": "그거 부작용은?"}]

AMBIGUOUS_MESSAGES_WITH_HISTORY = [
    {"role": "user", "content": "타이레놀 알려줘"},
    {"role": "assistant", "content": "타이레놀은 ..."},
    {"role": "user", "content": "그거 부작용은?"},
]

MEDICAL_CONTEXT = """[사용자 의학 컨텍스트]
- 복용 중인 약: 메트포민, 와파린, 오메가3
- 기저질환: 당뇨, 고혈압
- 알레르기: 페니실린
- 흡연: 비흡연
- 음주: 비음주
"""


class TestSchemaSanity:
    """IntentClassification Pydantic schema 자체 검증 (실 동작 X, schema 만)."""

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
        """Pydantic max_length=10 강제 검증."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IntentClassification(
                intent=IntentType.DOMAIN_QUESTION,
                fanout_queries=[f"q{i}" for i in range(11)],
            )


class TestClassifyIntent:
    """classify_intent 단위 테스트 (Red 상태)."""

    @pytest.mark.asyncio
    async def test_greeting(self) -> None:
        """'안녕' → intent=greeting, direct_answer 채움."""
        with pytest.raises(NotImplementedError):
            await classify_intent(GREETING_MESSAGES)

    @pytest.mark.asyncio
    async def test_domain_question_with_context(self) -> None:
        """도메인 질문 + 의학 컨텍스트 → fanout_queries 생성."""
        with pytest.raises(NotImplementedError):
            await classify_intent(DOMAIN_QUESTION_MESSAGES, medical_context=MEDICAL_CONTEXT)

    @pytest.mark.asyncio
    async def test_ambiguous_no_referent(self) -> None:
        """history 빈 + 대명사만 → intent=ambiguous + 명확화 질문."""
        with pytest.raises(NotImplementedError):
            await classify_intent(AMBIGUOUS_MESSAGES_NO_HISTORY)

    @pytest.mark.asyncio
    async def test_referent_resolution_from_history(self) -> None:
        """history 에 '타이레놀' 있을 때 → referent_resolution={'그거': '타이레놀'}."""
        with pytest.raises(NotImplementedError):
            await classify_intent(AMBIGUOUS_MESSAGES_WITH_HISTORY)

    @pytest.mark.asyncio
    async def test_negative_response_excluded(self) -> None:
        """is_smoking=False, is_drinking=False 인 컨텍스트 → 흡연/음주 query 안 만듦."""
        ctx = """[사용자 의학 컨텍스트]
- 복용 중인 약: 타이레놀
- 흡연: 비흡연
- 음주: 비음주
"""
        with pytest.raises(NotImplementedError):
            await classify_intent(DOMAIN_QUESTION_MESSAGES, medical_context=ctx)

    @pytest.mark.asyncio
    async def test_chronic_patient_cap_10(self) -> None:
        """만성질환자 컨텍스트 (복용약 12 + 기저질환 5 + 알레르기 2)
        → fanout_queries 정확히 10개 (cap)."""
        ctx = """[사용자 의학 컨텍스트]
- 복용 중인 약: 메트포민, 와파린, 오메가3, 아스피린, 라식스, 디고신, 메토프롤롤,
  암로디핀, 로수바스타틴, 메트프로민, 클로피도그렐, 오메프라졸
- 기저질환: 당뇨, 고혈압, 심장질환, 신장질환, 뇌혈관질환
- 알레르기: 페니실린, 설파제
"""
        with pytest.raises(NotImplementedError):
            await classify_intent(DOMAIN_QUESTION_MESSAGES, medical_context=ctx)
