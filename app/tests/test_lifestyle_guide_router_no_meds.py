"""LifestyleGuide — 활성 약물 부재 시 409 응답 단위 테스트.

배포 환경 회귀 가드:
    `POST /api/v1/lifestyle-guides/generate` 가 medications 0건일 때
    500 Internal Server Error 를 던지던 버그를 409 Conflict +
    구조화된 detail (code / message / redirect_to) 로 교체했다.
    FE 가 이 응답을 보고 토스트 + 라우팅을 한 번에 처리한다.

설계 결정 (PR #86 + #88 통합):
    Service 가 직접 ``HTTPException(409, detail={...})`` 을 raise 하고,
    router 는 그대로 propagate 한다 (single source of truth). 따라서
    실제 동작 검증은 service 단에서 수행하고, router 는 happy-path 만
    얇게 검증한다.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException, status
import pytest

from app.apis.v1.lifestyle_guide_routers import enqueue_guide
from app.services.lifestyle_guide_service import LifestyleGuideService


class TestServiceNoActiveMedications:
    """Service 단 — 활성 약물 부재 → 409 + 구조화된 detail."""

    def _service_with_empty_medications(self) -> LifestyleGuideService:
        # __init__ 우회 — RQ Queue 등 외부 의존성 instantiate 안 함.
        # active 0건 분기는 medication_repo 만 검사하므로 다른 attr 불필요.
        service = LifestyleGuideService.__new__(LifestyleGuideService)
        service.medication_repo = MagicMock()
        service.medication_repo.get_active_by_profile = AsyncMock(return_value=[])
        return service

    @pytest.mark.asyncio
    async def test_raises_409_when_no_active_medications(self) -> None:
        """active medications 0건 → HTTPException(409)."""
        service = self._service_with_empty_medications()

        with pytest.raises(HTTPException) as exc_info:
            await service.enqueue_guide_generation(profile_id=uuid4())

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_response_detail_has_required_keys(self) -> None:
        """detail 에 code / message / redirect_to 가 포함되어야 한다 (FE 계약)."""
        service = self._service_with_empty_medications()

        with pytest.raises(HTTPException) as exc_info:
            await service.enqueue_guide_generation(profile_id=uuid4())

        detail = exc_info.value.detail
        assert isinstance(detail, dict), f"detail must be dict, got {type(detail)}"
        assert detail["code"] == "NO_ACTIVE_MEDICATIONS"
        assert "처방전" in detail["message"]
        assert detail["redirect_to"] == "/ocr"


class TestEnqueueGuideHappyPath:
    """Router 단 happy path — service 가 guide 반환 시 그대로 반환."""

    @pytest.mark.asyncio
    async def test_returns_pending_response_on_success(self) -> None:
        guide_id = uuid4()
        service = MagicMock()
        guide = MagicMock(id=guide_id)
        service.enqueue_guide_with_owner_check = AsyncMock(return_value=guide)
        account = MagicMock(id=uuid4())

        result: Any = await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        assert result.id == guide_id

    @pytest.mark.asyncio
    async def test_propagates_service_http_exception(self) -> None:
        """Service 가 던진 HTTPException 은 router 가 그대로 propagate."""
        service = MagicMock()
        service.enqueue_guide_with_owner_check = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "NO_ACTIVE_MEDICATIONS", "message": "...", "redirect_to": "/ocr"},
            ),
        )
        account = MagicMock(id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert exc_info.value.detail["code"] == "NO_ACTIVE_MEDICATIONS"
