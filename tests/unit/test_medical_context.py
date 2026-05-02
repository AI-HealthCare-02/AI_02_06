"""Unit tests for app.services.chat.medical_context — medication + survey 빌더.

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 Tortoise ORM mock 또는 in-memory DB 로 검증.

PLAN.md §4.1 — medical_context 의 4가지 의도된 동작:
- profile.health_survey = None → 사용자 컨텍스트 섹션 생략 (빈 문자열)
- medication 0개 + health_survey 일부 → 일부 섹션만
- 모든 데이터 → '[사용자 의학 컨텍스트]' 한국어 markdown
- 음성응답 (is_smoking=False) 도 raw fact 로 그대로 포함 (IntentClassifier 가
  query 화 결정 — 본 빌더는 raw fact 만 노출)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.services.chat.medical_context import build_medical_context

SAMPLE_PROFILE_ID: UUID = uuid4()


class TestBuildMedicalContext:
    """build_medical_context 단위 테스트 (Red 상태)."""

    @pytest.mark.asyncio
    async def test_full_context(self) -> None:
        """medication + health_survey 모두 채워짐 → 6 섹션 markdown."""
        with pytest.raises(NotImplementedError):
            await build_medical_context(SAMPLE_PROFILE_ID)

    @pytest.mark.asyncio
    async def test_no_health_survey(self) -> None:
        """profile.health_survey = None → medication 만 출력."""
        with pytest.raises(NotImplementedError):
            await build_medical_context(SAMPLE_PROFILE_ID)

    @pytest.mark.asyncio
    async def test_no_medication(self) -> None:
        """medication 0개 + health_survey 일부 → health_survey 섹션만."""
        with pytest.raises(NotImplementedError):
            await build_medical_context(SAMPLE_PROFILE_ID)

    @pytest.mark.asyncio
    async def test_empty_profile(self) -> None:
        """medication 0 + health_survey None → 빈 문자열 (섹션 자체 생략)."""
        with pytest.raises(NotImplementedError):
            await build_medical_context(SAMPLE_PROFILE_ID)
