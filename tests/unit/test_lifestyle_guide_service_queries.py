"""Unit tests for LifestyleGuideService ownership-check query methods.

Tests cover:
- generate_guide_with_owner_check
- get_guide_with_owner_check
- get_latest_guide_with_owner_check
- list_guides_with_owner_check
- get_guide_challenges_with_owner_check

All tests are RED until the methods are implemented.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.services.lifestyle_guide_service import LifestyleGuideService

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_profile(account_id=None):
    """Build a minimal mock Profile."""
    p = MagicMock()
    p.id = uuid4()
    p.account_id = account_id or uuid4()
    return p


def _make_guide(profile_id=None):
    """Build a minimal mock LifestyleGuide."""
    g = MagicMock()
    g.id = uuid4()
    g.profile_id = profile_id or uuid4()
    return g


def _make_challenge():
    """Build a minimal mock Challenge."""
    c = MagicMock()
    c.id = uuid4()
    return c


# ── Fixture ────────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> LifestyleGuideService:
    """LifestyleGuideService with all external dependencies mocked."""
    svc = LifestyleGuideService.__new__(LifestyleGuideService)
    svc.medication_repo = AsyncMock()
    svc.guide_repo = AsyncMock()
    svc.challenge_repo = AsyncMock()
    svc.llm_client = AsyncMock()
    svc.profile_repo = AsyncMock()
    return svc


# ── generate_guide_with_owner_check ───────────────────────────────────────


async def test_generate_guide_with_owner_check_success(
    service: LifestyleGuideService,
) -> None:
    """소유자 확인 후 가이드를 생성해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    guide = _make_guide(profile_id=profile.id)

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.medication_repo.get_active_by_profile = AsyncMock(
        return_value=[
            MagicMock(medicine_name="타이레놀", category="해열진통제", intake_instruction="식후", dose_per_intake="1정")
        ]
    )
    service.llm_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=(
                            '{"diet":"저염식","sleep":"규칙 수면","exercise":"유산소","symptom":"혈압 측정",'
                            '"interaction":"자몽 금지","recommended_challenges":[]}'
                        )
                    )
                )
            ]
        )
    )
    service.guide_repo.create = AsyncMock(return_value=guide)
    service.challenge_repo.bulk_create_from_guide = AsyncMock(return_value=[])

    result = await service.generate_guide_with_owner_check(profile.id, account_id)

    assert result is guide


async def test_generate_guide_with_owner_check_profile_not_found(
    service: LifestyleGuideService,
) -> None:
    """프로필이 존재하지 않으면 HTTP 404를 발생시켜야 한다."""
    service.profile_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.generate_guide_with_owner_check(uuid4(), uuid4())

    assert exc_info.value.status_code == 404


async def test_generate_guide_with_owner_check_forbidden(
    service: LifestyleGuideService,
) -> None:
    """다른 계정의 프로필이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())  # different account
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.generate_guide_with_owner_check(profile.id, uuid4())

    assert exc_info.value.status_code == 403


# ── get_guide_with_owner_check ─────────────────────────────────────────────


async def test_get_guide_with_owner_check_success(
    service: LifestyleGuideService,
) -> None:
    """가이드와 소유권 확인 후 가이드를 반환해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    guide = _make_guide(profile_id=profile.id)

    service.guide_repo.get_by_id = AsyncMock(return_value=guide)
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    result = await service.get_guide_with_owner_check(guide.id, account_id)

    assert result is guide


async def test_get_guide_with_owner_check_guide_not_found(
    service: LifestyleGuideService,
) -> None:
    """가이드가 없으면 HTTP 404를 발생시켜야 한다."""
    service.guide_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_guide_with_owner_check(uuid4(), uuid4())

    assert exc_info.value.status_code == 404


async def test_get_guide_with_owner_check_forbidden(
    service: LifestyleGuideService,
) -> None:
    """다른 계정의 가이드이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())  # different account
    guide = _make_guide(profile_id=profile.id)

    service.guide_repo.get_by_id = AsyncMock(return_value=guide)
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_guide_with_owner_check(guide.id, uuid4())

    assert exc_info.value.status_code == 403


# ── get_latest_guide_with_owner_check ─────────────────────────────────────


async def test_get_latest_guide_with_owner_check_success(
    service: LifestyleGuideService,
) -> None:
    """소유권 확인 후 최신 가이드를 반환해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    guide = _make_guide(profile_id=profile.id)

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.guide_repo.get_latest_by_profile = AsyncMock(return_value=guide)

    result = await service.get_latest_guide_with_owner_check(profile.id, account_id)

    assert result is guide


async def test_get_latest_guide_with_owner_check_no_guide(
    service: LifestyleGuideService,
) -> None:
    """가이드가 없으면 HTTP 404를 발생시켜야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.guide_repo.get_latest_by_profile = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_latest_guide_with_owner_check(profile.id, account_id)

    assert exc_info.value.status_code == 404


async def test_get_latest_guide_with_owner_check_forbidden(
    service: LifestyleGuideService,
) -> None:
    """다른 계정의 프로필이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_latest_guide_with_owner_check(profile.id, uuid4())

    assert exc_info.value.status_code == 403


# ── list_guides_with_owner_check ──────────────────────────────────────────


async def test_list_guides_with_owner_check_success(
    service: LifestyleGuideService,
) -> None:
    """소유권 확인 후 가이드 목록을 반환해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    guides = [_make_guide(profile_id=profile.id), _make_guide(profile_id=profile.id)]

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.guide_repo.get_all_by_profile = AsyncMock(return_value=guides)

    result = await service.list_guides_with_owner_check(profile.id, account_id)

    assert result == guides
    assert len(result) == 2


async def test_list_guides_with_owner_check_forbidden(
    service: LifestyleGuideService,
) -> None:
    """다른 계정의 프로필이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.list_guides_with_owner_check(profile.id, uuid4())

    assert exc_info.value.status_code == 403


# ── get_guide_challenges_with_owner_check ─────────────────────────────────


async def test_get_guide_challenges_with_owner_check_success(
    service: LifestyleGuideService,
) -> None:
    """소유권 확인 후 가이드에 연결된 챌린지 목록을 반환해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    guide = _make_guide(profile_id=profile.id)
    challenges = [_make_challenge(), _make_challenge()]

    service.guide_repo.get_by_id = AsyncMock(return_value=guide)
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.challenge_repo.get_by_guide_id = AsyncMock(return_value=challenges)

    result = await service.get_guide_challenges_with_owner_check(guide.id, account_id)

    assert result == challenges
    service.challenge_repo.get_by_guide_id.assert_called_once_with(guide.id)


async def test_get_guide_challenges_with_owner_check_guide_not_found(
    service: LifestyleGuideService,
) -> None:
    """가이드가 없으면 HTTP 404를 발생시켜야 한다."""
    service.guide_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_guide_challenges_with_owner_check(uuid4(), uuid4())

    assert exc_info.value.status_code == 404


async def test_get_guide_challenges_with_owner_check_forbidden(
    service: LifestyleGuideService,
) -> None:
    """다른 계정의 가이드이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())
    guide = _make_guide(profile_id=profile.id)

    service.guide_repo.get_by_id = AsyncMock(return_value=guide)
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_guide_challenges_with_owner_check(guide.id, uuid4())

    assert exc_info.value.status_code == 403
