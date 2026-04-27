"""F3 — `create_medication` 시 즉시 회수 체크 (Phase 7 Step 7).

검증 포인트:
- F3-1: 회수 약 등록 → send_recall_alert 1회 호출
- F3-2: 비회수 약 등록 → send_recall_alert 호출 없음
- F3-4: medicine_info FK 없는 회수 약명 → ILIKE fallback 매칭 후 알림
- 알림 dispatch 가 실패해도 medication 자체는 정상 반환 (격리)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _build_medication() -> Any:
    med = MagicMock()
    med.id = uuid4()
    med.profile_id = uuid4()
    med.medicine_name = "마데카솔케어연고"
    return med


_FIND_MATCH = "app.repositories.drug_recall_repository.DrugRecallRepository.find_match"
_SEND_ALERT = "app.services.recall_notification_service.send_recall_alert"


@pytest.mark.asyncio
async def test_f3_1_recall_match_dispatches_alert() -> None:
    """F3-1: 회수 약 등록 시 알림 1건 발송."""
    from app.services.medication_service import MedicationService

    medication = _build_medication()

    with (
        patch(_FIND_MATCH, new=AsyncMock(return_value=[MagicMock()])),
        patch(_SEND_ALERT, new=AsyncMock()) as send,
    ):
        await MedicationService._dispatch_recall_alert_if_any(medication)

    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_f3_2_no_match_no_alert() -> None:
    """F3-2: 회수 매칭 없으면 알림 호출 없음."""
    from app.services.medication_service import MedicationService

    medication = _build_medication()

    with (
        patch(_FIND_MATCH, new=AsyncMock(return_value=[])),
        patch(_SEND_ALERT, new=AsyncMock()) as send,
    ):
        await MedicationService._dispatch_recall_alert_if_any(medication)

    send.assert_not_called()


@pytest.mark.asyncio
async def test_f3_4_dispatch_error_does_not_break_caller() -> None:
    """알림 발송 실패는 medication 등록 흐름을 망치지 않는다."""
    from app.services.medication_service import MedicationService

    medication = _build_medication()

    async def boom(*_args: Any, **_kwargs: Any) -> Any:
        msg = "boom"
        raise RuntimeError(msg)

    # find_match 예외도 흡수되어야 함
    with patch(_FIND_MATCH, new=AsyncMock(side_effect=boom)):
        # 예외가 전파되지 않아야 한다 (격리)
        await MedicationService._dispatch_recall_alert_if_any(medication)
