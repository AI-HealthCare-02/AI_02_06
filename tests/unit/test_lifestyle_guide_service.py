"""Unit tests for LifestyleGuideService.generate_guide().

Tests verify the full guide generation flow using mocked dependencies:
- active medication query → LLM call → guide save → challenge bulk-create.

All tests are intentionally RED until the module and its dependencies are implemented.
"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.lifestyle_guide_service import LifestyleGuideService

# ── Shared LLM response fixture ────────────────────────────────────────────

_VALID_LLM_JSON = {
    "diet": "저염식 권장",
    "sleep": "규칙적 수면 유지",
    "exercise": "저강도 유산소 추천",
    "symptom": "혈압 매일 측정",
    "interaction": "자몽 섭취 금지",
    "recommended_challenges": [
        {
            "category": "diet",
            "title": "저염식 7일 챌린지",
            "description": "하루 나트륨 2g 이하 식단",
            "target_days": 7,
            "difficulty": "보통",
        },
        {
            "category": "exercise",
            "title": "30분 걷기",
            "description": "매일 30분 걷기",
            "target_days": 14,
            "difficulty": "쉬움",
        },
    ],
}


def _make_llm_response(content: dict) -> MagicMock:
    """Build a mock OpenAI chat.completions.create response."""
    choice = MagicMock()
    choice.message.content = json.dumps(content, ensure_ascii=False)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_medication(name: str = "타이레놀") -> MagicMock:
    """Build a minimal mock Medication ORM object."""
    med = MagicMock()
    med.medicine_name = name
    med.category = "해열진통제"
    med.intake_instruction = "식후 30분"
    med.dose_per_intake = "1정"
    return med


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> LifestyleGuideService:
    """LifestyleGuideService with all external dependencies mocked."""
    svc = LifestyleGuideService.__new__(LifestyleGuideService)
    svc.medication_repo = AsyncMock()
    svc.guide_repo = AsyncMock()
    svc.challenge_repo = AsyncMock()
    svc.llm_client = AsyncMock()
    return svc


@pytest.fixture
def mock_guide() -> MagicMock:
    guide = MagicMock()
    guide.id = uuid4()
    return guide


# ── 정상 케이스 ────────────────────────────────────────────────────────────


async def test_generate_guide_returns_lifestyle_guide(
    service: LifestyleGuideService,
    mock_guide: MagicMock,
) -> None:
    """generate_guide는 LifestyleGuide 객체를 반환해야 한다."""
    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[_make_medication()]
    )
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=_make_llm_response(_VALID_LLM_JSON)
    )
    service.guide_repo.create = AsyncMock(return_value=mock_guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    result = await service.generate_guide(profile_id)

    assert result is mock_guide


async def test_generate_guide_calls_guide_repo_create(
    service: LifestyleGuideService,
    mock_guide: MagicMock,
) -> None:
    """guide_repo.create가 profile_id, content, medication_snapshot과 함께 호출되어야 한다."""
    profile_id = uuid4()
    med = _make_medication("암로디핀")
    service.medication_repo.get_active_by_profile = AsyncMock(return_value=[med])
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=_make_llm_response(_VALID_LLM_JSON)
    )
    service.guide_repo.create = AsyncMock(return_value=mock_guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    await service.generate_guide(profile_id)

    service.guide_repo.create.assert_called_once()
    call_kwargs = service.guide_repo.create.call_args.kwargs
    assert call_kwargs["profile_id"] == profile_id
    assert "content" in call_kwargs
    assert "medication_snapshot" in call_kwargs


async def test_generate_guide_calls_bulk_create_challenges(
    service: LifestyleGuideService,
    mock_guide: MagicMock,
) -> None:
    """challenge_repo.bulk_create_from_guide가 guide_id, profile_id, challenges와 함께 호출되어야 한다."""
    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[_make_medication()]
    )
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=_make_llm_response(_VALID_LLM_JSON)
    )
    service.guide_repo.create = AsyncMock(return_value=mock_guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    await service.generate_guide(profile_id)

    service.challenge_repo.bulk_create_from_guide.assert_called_once()
    call_kwargs = service.challenge_repo.bulk_create_from_guide.call_args.kwargs
    assert call_kwargs["guide_id"] == mock_guide.id
    assert call_kwargs["profile_id"] == profile_id
    assert len(call_kwargs["challenges"]) == 2  # 2 challenges in _VALID_LLM_JSON


async def test_generate_guide_calls_llm_once(
    service: LifestyleGuideService,
    mock_guide: MagicMock,
) -> None:
    """GPT 클라이언트는 정확히 한 번 호출되어야 한다."""
    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[_make_medication()]
    )
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=_make_llm_response(_VALID_LLM_JSON)
    )
    service.guide_repo.create = AsyncMock(return_value=mock_guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    await service.generate_guide(profile_id)

    service.llm_client.chat.completions.create.assert_called_once()


async def test_generate_guide_medication_snapshot_contains_all_meds(
    service: LifestyleGuideService,
    mock_guide: MagicMock,
) -> None:
    """medication_snapshot에 모든 활성 약물 정보가 포함되어야 한다."""
    profile_id = uuid4()
    meds = [_make_medication("타이레놀"), _make_medication("암로디핀")]
    service.medication_repo.get_active_by_profile = AsyncMock(return_value=meds)
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=_make_llm_response(_VALID_LLM_JSON)
    )
    service.guide_repo.create = AsyncMock(return_value=mock_guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    await service.generate_guide(profile_id)

    snapshot = service.guide_repo.create.call_args.kwargs["medication_snapshot"]
    assert len(snapshot) == 2


# ── 예외 케이스 ────────────────────────────────────────────────────────────


async def test_generate_guide_raises_on_no_active_meds(
    service: LifestyleGuideService,
) -> None:
    """활성 약물이 없으면 ValueError를 발생시켜야 한다."""
    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(return_value=[])

    with pytest.raises(ValueError, match="활성 약물"):
        await service.generate_guide(profile_id)


async def test_generate_guide_raises_on_llm_error(
    service: LifestyleGuideService,
) -> None:
    """LLM 호출 실패 시 ValueError를 발생시켜야 한다."""
    from openai import OpenAIError

    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[_make_medication()]
    )
    service.llm_client.chat.completions.create = AsyncMock(
        side_effect=OpenAIError("connection timeout")
    )

    with pytest.raises(ValueError, match="가이드 생성"):
        await service.generate_guide(profile_id)


async def test_generate_guide_raises_on_invalid_llm_json(
    service: LifestyleGuideService,
) -> None:
    """LLM이 잘못된 JSON을 반환하면 ValueError를 발생시켜야 한다."""
    profile_id = uuid4()
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[_make_medication()]
    )
    bad_response = MagicMock()
    bad_response.choices[0].message.content = "not valid json {{"
    service.llm_client.chat.completions.create = AsyncMock(return_value=bad_response)

    with pytest.raises(ValueError, match="가이드 생성"):
        await service.generate_guide(profile_id)
