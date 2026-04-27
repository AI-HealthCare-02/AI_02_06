"""Recall notification dispatcher (Phase 7).

Persists "회수 발생" 시스템 메시지 as ``ChatMessage`` rows with a
distinguishable ``metadata.kind="recall_alert"`` so the existing
chat-history UI / SSE plumbing can render them without schema changes.

Sender encoding:
    - ``sender_type=ASSISTANT`` (the model only has USER/ASSISTANT;
      no migration needed).
    - ``metadata.kind="recall_alert"`` separates these from regular
      assistant turns and gives FE a render hook.

Dedup strategy (cron-F3):
    - Each notification row stores ``recall_item_seq``,
      ``recall_command_date``, ``recall_reason`` and ``medication_id``
      in metadata.
    - Before insert, the service checks whether a row with the same
      ``(profile_id, recall_item_seq, recall_command_date,
      recall_reason, medication_id)`` already exists for the user's
      messages. If yes → skip.

Session resolution:
    - The service grabs the user's most recent (non-soft-deleted)
      ``ChatSession`` and writes there. If none exists, the alert is
      silently skipped with a warning log — recall alerts assume the
      user has at least one chat session.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from tortoise.expressions import Q

from app.models.chat_sessions import ChatSession
from app.models.messages import ChatMessage, SenderType

logger = logging.getLogger(__name__)

# Metadata 에 노출되는 알림 종류 식별 키
RECALL_ALERT_KIND = "recall_alert"


def _format_recall_message(recall: Any, medication_name: str) -> str:
    """Render the user-facing alert text in Korean.

    The format is intentionally short so the chat UI can show it as a
    single bubble. Date `YYYYMMDD` → `YYYY-MM-DD` for readability.
    """
    raw_date = recall.recall_command_date or ""
    date_str = (
        f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 and raw_date.isdigit() else raw_date
    )
    reason = recall.recall_reason or "사유 미기재"
    return f"[안전 알림] {medication_name}이(가) 식약처에서 {reason}로 {date_str} 회수되었습니다."


async def _already_notified(
    *,
    profile_id: UUID,
    recall: Any,
    medication_id: UUID | None,
) -> bool:
    """Return True when this exact recall + medication pair has already
    produced a notification for this profile.
    """
    qs = ChatMessage.filter(
        session__profile_id=profile_id,
        deleted_at__isnull=True,
        metadata__kind=RECALL_ALERT_KIND,
        metadata__recall_item_seq=recall.item_seq,
        metadata__recall_command_date=recall.recall_command_date,
        metadata__recall_reason=recall.recall_reason,
    )
    if medication_id is not None:
        qs = qs.filter(metadata__medication_id=str(medication_id))
    return await qs.exists()


async def _resolve_target_session_id(profile_id: UUID) -> UUID | None:
    """Return the most recent live chat-session for this profile."""
    session = await ChatSession.filter(profile_id=profile_id, deleted_at__isnull=True).order_by("-created_at").first()
    return session.id if session else None


async def send_recall_alert(
    *,
    profile_id: UUID,
    recall: Any,
    medication: Any | None = None,
) -> ChatMessage | None:
    """Insert one recall-alert ``ChatMessage`` for the user.

    Args:
        profile_id: Receiver.
        recall: ``DrugRecall`` row (Tortoise model or Mock-equivalent).
        medication: Optional ``Medication`` row that triggered the
            alert. Used for ``medicine_name`` display + dedup key.

    Returns:
        The created ``ChatMessage`` row, or ``None`` if the alert was
        skipped (already sent / no chat session).
    """
    medication_id: UUID | None = getattr(medication, "id", None)
    medicine_name = getattr(medication, "medicine_name", None) or recall.product_name or "(이름 없음)"

    if await _already_notified(profile_id=profile_id, recall=recall, medication_id=medication_id):
        logger.info(
            "[RecallAlert] dedup hit profile=%s item_seq=%s reason=%s",
            profile_id,
            recall.item_seq,
            recall.recall_reason,
        )
        return None

    session_id = await _resolve_target_session_id(profile_id)
    if session_id is None:
        logger.warning("[RecallAlert] no active chat session for profile=%s — skip", profile_id)
        return None

    message = await ChatMessage.create(
        session_id=session_id,
        sender_type=SenderType.ASSISTANT,
        content=_format_recall_message(recall, medicine_name),
        metadata={
            "kind": RECALL_ALERT_KIND,
            "recall_item_seq": recall.item_seq,
            "recall_command_date": recall.recall_command_date,
            "recall_reason": recall.recall_reason,
            "medication_id": str(medication_id) if medication_id else None,
            "product_name": recall.product_name,
            "entrps_name": recall.entrps_name,
            "issued_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    logger.info(
        "[RecallAlert] dispatched profile=%s item_seq=%s reason=%s",
        profile_id,
        recall.item_seq,
        recall.recall_reason,
    )
    return message


# ── Cron 진입점 ─────────────────────────────────────────────────────


async def dispatch_for_recall(recall: Any) -> int:
    """For one new recall row, send alerts to every affected user.

    Walks through all `medications.medicine_name` matches:
        1. exact `medicine_name == recall.product_name`
        2. medicine_info join: medicine_info.item_seq == recall.item_seq
           → medicine_name → medication match
    Both stages tolerate misses (S7 OCR-only entries are caught by
    stage 1 ILIKE).

    Returns:
        Number of alerts actually inserted (after dedup).
    """
    from app.models.medication import Medication
    from app.models.medicine_info import MedicineInfo

    candidate_names: set[str] = {recall.product_name} if recall.product_name else set()
    if recall.item_seq:
        rows = await MedicineInfo.filter(item_seq=recall.item_seq).all()
        for r in rows:
            if r.medicine_name:
                candidate_names.add(r.medicine_name)

    if not candidate_names:
        return 0

    name_filter = Q(medicine_name__in=candidate_names) | Q(medicine_name__icontains=recall.product_name)
    medications = await Medication.filter(Q(deleted_at__isnull=True) & name_filter).all()

    inserted = 0
    for med in medications:
        result = await send_recall_alert(
            profile_id=med.profile_id,
            recall=recall,
            medication=med,
        )
        if result is not None:
            inserted += 1
    return inserted
