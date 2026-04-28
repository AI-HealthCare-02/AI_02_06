"""LifestyleGuide 라우터 — 활성 약물 부재 시 409 응답 단위 테스트.

배포 환경 회귀 가드:
    `POST /api/v1/lifestyle-guides/generate` 가 medications 0건일 때
    500 Internal Server Error 를 던지던 버그를 409 Conflict +
    구조화된 detail (code / message / redirect_to) 로 교체했다.
    FE 가 이 응답을 보고 토스트 + 라우팅을 한 번에 처리한다.

본 테스트는 라우터 핸들러를 service 만 mock 으로 바꿔 직접 호출한다.
실제 FastAPI app/middleware/DB 는 띄우지 않는다 (CI 비용 0).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException, status
import pytest

from app.apis.v1.lifestyle_guide_routers import enqueue_guide


class TestEnqueueGuideNoActiveMedications:
    """활성 약물 부재 → 409 + 구조화된 detail."""

    @pytest.mark.asyncio
    async def test_value_error_translated_to_409(self) -> None:
        """service 가 ValueError 던지면 라우터가 409 로 변환해야 한다."""
        service = MagicMock()
        service.enqueue_guide_with_owner_check = AsyncMock(
            side_effect=ValueError("활성 약물 목록이 비어 있습니다."),
        )
        account = MagicMock(id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_response_detail_has_required_keys(self) -> None:
        """detail 에 code / message / redirect_to 가 포함되어야 한다 (FE 계약)."""
        service = MagicMock()
        service.enqueue_guide_with_owner_check = AsyncMock(side_effect=ValueError("dummy"))
        account = MagicMock(id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        detail = exc_info.value.detail
        assert isinstance(detail, dict), f"detail must be dict, got {type(detail)}"
        assert detail["code"] == "NO_ACTIVE_MEDICATIONS"
        assert "처방전" in detail["message"]
        assert detail["redirect_to"] == "/ocr"
        assert detail["service_message"] == "dummy"

    @pytest.mark.asyncio
    async def test_chains_exception_for_logging(self) -> None:
        """원본 ValueError 가 ``__cause__`` 에 보존되어야 (서버 로그 디버깅)."""
        original = ValueError("활성 약물 목록이 비어 있습니다.")
        service = MagicMock()
        service.enqueue_guide_with_owner_check = AsyncMock(side_effect=original)
        account = MagicMock(id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        assert exc_info.value.__cause__ is original


class TestEnqueueGuideHappyPath:
    """정상 경로 — service 가 guide 반환 시 라우터가 그대로 반환."""

    @pytest.mark.asyncio
    async def test_returns_pending_response_on_success(self) -> None:
        guide_id = uuid4()
        service = MagicMock()
        guide = MagicMock(id=guide_id)
        service.enqueue_guide_with_owner_check = AsyncMock(return_value=guide)
        account = MagicMock(id=uuid4())

        result: Any = await enqueue_guide(profile_id=uuid4(), current_account=account, service=service)

        assert result.id == guide_id
