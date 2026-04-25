"""Unit tests for DailySymptomLogService.

Tests cover create_log_with_owner_check and get_recent_logs_with_owner_check,
verifying ownership enforcement and repository delegation.

All tests are RED until the service is implemented.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.services.daily_symptom_log_service import DailySymptomLogService

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_profile(account_id=None):
    """Build a minimal mock Profile."""
    p = MagicMock()
    p.id = uuid4()
    p.account_id = account_id or uuid4()
    return p


def _make_log():
    """Build a minimal mock DailySymptomLog."""
    log = MagicMock()
    log.id = uuid4()
    return log


def _make_create_data(profile_id=None):
    """Build a minimal DailySymptomLogCreate-like object."""
    data = MagicMock()
    data.profile_id = profile_id or uuid4()
    data.log_date = datetime.now(tz=UTC).date()
    data.symptoms = ["두통", "메스꺼움"]
    data.note = "테스트 노트"
    return data


# ── Fixture ────────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> DailySymptomLogService:
    """DailySymptomLogService with all external dependencies mocked."""
    svc = DailySymptomLogService.__new__(DailySymptomLogService)
    svc.log_repo = AsyncMock()
    svc.profile_repo = AsyncMock()
    return svc


# ── create_log_with_owner_check ───────────────────────────────────────────


async def test_create_log_success(service: DailySymptomLogService) -> None:
    """소유권 확인 후 증상 기록을 생성해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    data = _make_create_data(profile_id=profile.id)
    created_log = _make_log()

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.log_repo.create = AsyncMock(return_value=created_log)

    result = await service.create_log_with_owner_check(profile.id, account_id, data)

    assert result is created_log


async def test_create_log_calls_repo_with_correct_args(
    service: DailySymptomLogService,
) -> None:
    """log_repo.create가 올바른 인자로 호출되어야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    data = _make_create_data(profile_id=profile.id)
    created_log = _make_log()

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.log_repo.create = AsyncMock(return_value=created_log)

    await service.create_log_with_owner_check(profile.id, account_id, data)

    service.log_repo.create.assert_called_once()
    call_kwargs = service.log_repo.create.call_args.kwargs
    assert call_kwargs["profile_id"] == profile.id
    assert call_kwargs["log_date"] == data.log_date
    assert call_kwargs["symptoms"] == data.symptoms
    assert call_kwargs["note"] == data.note


async def test_create_log_profile_not_found(
    service: DailySymptomLogService,
) -> None:
    """프로필이 없으면 HTTP 404를 발생시켜야 한다."""
    service.profile_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_log_with_owner_check(uuid4(), uuid4(), _make_create_data())

    assert exc_info.value.status_code == 404


async def test_create_log_forbidden(service: DailySymptomLogService) -> None:
    """다른 계정의 프로필이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_log_with_owner_check(profile.id, uuid4(), _make_create_data(profile_id=profile.id))

    assert exc_info.value.status_code == 403


# ── get_recent_logs_with_owner_check ─────────────────────────────────────


async def test_get_recent_logs_success(service: DailySymptomLogService) -> None:
    """소유권 확인 후 최근 N일 기록 목록을 반환해야 한다."""
    account_id = uuid4()
    profile = _make_profile(account_id=account_id)
    logs = [_make_log(), _make_log(), _make_log()]

    service.profile_repo.get_by_id = AsyncMock(return_value=profile)
    service.log_repo.get_recent_by_profile = AsyncMock(return_value=logs)

    result = await service.get_recent_logs_with_owner_check(profile.id, account_id, days=30)

    assert result == logs
    service.log_repo.get_recent_by_profile.assert_called_once_with(profile_id=profile.id, days=30)


async def test_get_recent_logs_forbidden(service: DailySymptomLogService) -> None:
    """다른 계정의 프로필이면 HTTP 403을 발생시켜야 한다."""
    profile = _make_profile(account_id=uuid4())
    service.profile_repo.get_by_id = AsyncMock(return_value=profile)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_recent_logs_with_owner_check(profile.id, uuid4(), days=30)

    assert exc_info.value.status_code == 403


async def test_get_recent_logs_profile_not_found(
    service: DailySymptomLogService,
) -> None:
    """프로필이 없으면 HTTP 404를 발생시켜야 한다."""
    service.profile_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_recent_logs_with_owner_check(uuid4(), uuid4(), days=7)

    assert exc_info.value.status_code == 404
