"""Recall notification dispatcher 단위 테스트 (Phase 7 Step 7).

검증 포인트:
- send_recall_alert: 알림 메시지 생성 + metadata 키 일관성
- dedup: 동일 (item_seq, recall_command_date, recall_reason, medication_id) 재호출 시 skip
- 세션 미존재 시 skip + warning
- 메시지 템플릿: "[안전 알림] {약품}이(가) 식약처에서 {사유}로 {날짜} 회수되었습니다."
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _recall(item_seq: str = "200903973") -> Any:
    row = MagicMock()
    row.item_seq = item_seq
    row.product_name = "마데카솔케어연고"
    row.entrps_name = "동국제약(주)"
    row.recall_reason = "포장재 불량(코팅 벗겨짐)"
    row.recall_command_date = "20260401"
    row.sale_stop_yn = "N"
    return row


def _medication(name: str = "마데카솔케어연고") -> Any:
    med = MagicMock()
    med.id = uuid4()
    med.medicine_name = name
    return med


# ── send_recall_alert ────────────────────────────────────────────────


class TestSendRecallAlert:
    @pytest.mark.asyncio
    async def test_inserts_message_with_metadata(self) -> None:
        from app.services import recall_notification_service as svc

        profile_id = uuid4()
        recall = _recall()
        medication = _medication()

        with (
            patch.object(svc, "_already_notified", new=AsyncMock(return_value=False)),
            patch.object(svc, "_resolve_target_session_id", new=AsyncMock(return_value=uuid4())),
            patch.object(svc.ChatMessage, "create", new=AsyncMock()) as create,
        ):
            await svc.send_recall_alert(profile_id=profile_id, recall=recall, medication=medication)

        create.assert_awaited_once()
        kw = create.await_args.kwargs
        assert kw["sender_type"] == svc.SenderType.ASSISTANT
        # 메시지 내용 검증
        assert "마데카솔케어연고" in kw["content"]
        assert "포장재 불량(코팅 벗겨짐)" in kw["content"]
        assert "2026-04-01" in kw["content"]
        # metadata 일관성
        meta = kw["metadata"]
        assert meta["kind"] == svc.RECALL_ALERT_KIND
        assert meta["recall_item_seq"] == "200903973"
        assert meta["recall_command_date"] == "20260401"
        assert meta["medication_id"] == str(medication.id)

    @pytest.mark.asyncio
    async def test_dedup_returns_none(self) -> None:
        """이미 보낸 알림이면 None 반환 + ChatMessage 생성 호출 X."""
        from app.services import recall_notification_service as svc

        with (
            patch.object(svc, "_already_notified", new=AsyncMock(return_value=True)),
            patch.object(svc.ChatMessage, "create", new=AsyncMock()) as create,
        ):
            result = await svc.send_recall_alert(profile_id=uuid4(), recall=_recall(), medication=_medication())

        assert result is None
        create.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_session_skips(self) -> None:
        """활성 chat session 이 없으면 skip + None."""
        from app.services import recall_notification_service as svc

        with (
            patch.object(svc, "_already_notified", new=AsyncMock(return_value=False)),
            patch.object(svc, "_resolve_target_session_id", new=AsyncMock(return_value=None)),
            patch.object(svc.ChatMessage, "create", new=AsyncMock()) as create,
        ):
            result = await svc.send_recall_alert(profile_id=uuid4(), recall=_recall(), medication=_medication())

        assert result is None
        create.assert_not_called()
