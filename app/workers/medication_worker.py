"""Medication batch worker module.

Handles automatic expiry and soft deletion of prescriptions at 00:10 KST.

Two passes:
  1. end_date < today AND is_active=True  → is_active=False
  2. expiration_date < today AND deleted_at IS NULL → deleted_at=now()
"""

from datetime import datetime
import logging

from app.core import config
from app.models.medication import Medication

logger = logging.getLogger(__name__)


async def expire_medications() -> None:
    """Deactivate and soft-delete expired medications.

    Pass 1: Medications whose end_date is in the past are deactivated.
    Pass 2: Medications whose expiration_date is in the past are soft-deleted.
    """
    today = datetime.now(tz=config.TIMEZONE).date()
    now = datetime.now(tz=config.TIMEZONE)

    # Pass 1: deactivate medications past end_date
    expired_active = await Medication.filter(
        is_active=True,
        deleted_at__isnull=True,
        end_date__lt=today,
        end_date__isnull=False,
    ).all()

    deactivated_count = 0
    for medication in expired_active:
        medication.is_active = False
        await medication.save()
        deactivated_count += 1

    # Pass 2: soft-delete medications past expiration_date
    to_delete = await Medication.filter(
        deleted_at__isnull=True,
        expiration_date__lt=today,
        expiration_date__isnull=False,
    ).all()

    deleted_count = 0
    for medication in to_delete:
        medication.deleted_at = now
        await medication.save()
        deleted_count += 1

    logger.info(
        "expire_medications completed: date=%s deactivated=%d soft_deleted=%d",
        today,
        deactivated_count,
        deleted_count,
    )
