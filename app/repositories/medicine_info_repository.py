"""Medicine info repository module.

This module provides data access layer for the medicine_info table,
handling drug information queries and bulk upsert operations
for public API data synchronization.
"""

from datetime import UTC, datetime
import logging

from app.models.data_sync_log import DataSyncLog
from app.models.medicine_info import MedicineInfo

logger = logging.getLogger(__name__)


class MedicineInfoRepository:
    """Medicine info database repository for drug data management."""

    async def get_by_id(self, medicine_id: int) -> MedicineInfo | None:
        """Get medicine info by ID.

        Args:
            medicine_id: Medicine info primary key.

        Returns:
            MedicineInfo if found, None otherwise.
        """
        return await MedicineInfo.filter(id=medicine_id).first()

    async def get_by_item_seq(self, item_seq: str) -> MedicineInfo | None:
        """Get medicine info by public API item sequence code.

        Args:
            item_seq: Drug product code from public API.

        Returns:
            MedicineInfo if found, None otherwise.
        """
        return await MedicineInfo.filter(item_seq=item_seq).first()

    async def get_by_name(self, medicine_name: str) -> MedicineInfo | None:
        """Get medicine info by exact name match.

        Args:
            medicine_name: Drug product name in Korean.

        Returns:
            MedicineInfo if found, None otherwise.
        """
        return await MedicineInfo.filter(medicine_name=medicine_name).first()

    async def search_by_name(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MedicineInfo]:
        """Search medicine info by partial name match.

        Args:
            query: Search keyword for drug name.
            limit: Maximum number of results.

        Returns:
            List of matching MedicineInfo records.
        """
        return (
            await MedicineInfo
            .filter(
                medicine_name__icontains=query,
            )
            .limit(limit)
            .all()
        )

    async def upsert_from_api(self, item_data: dict) -> tuple[MedicineInfo, bool]:
        """Insert or update a single medicine info record from API data.

        Uses item_seq as the unique key for upsert operations.

        Args:
            item_data: Transformed API data dictionary with model field names.

        Returns:
            Tuple of (MedicineInfo instance, created flag).
        """
        item_seq = item_data.pop("item_seq")
        item_data["last_synced_at"] = datetime.now(tz=UTC)

        instance, created = await MedicineInfo.update_or_create(
            defaults=item_data,
            item_seq=item_seq,
        )
        return instance, created

    async def bulk_upsert(
        self,
        items: list[dict],
        batch_size: int = 100,
    ) -> dict[str, int]:
        """Bulk upsert medicine info records from API data.

        Processes items in batches using update_or_create for each item.

        Args:
            items: List of transformed API data dictionaries.
            batch_size: Number of items to process before logging progress.

        Returns:
            Dictionary with 'inserted' and 'updated' counts.
        """
        inserted = 0
        updated = 0
        total = len(items)

        for idx, item_data in enumerate(items, start=1):
            try:
                _, created = await self.upsert_from_api(item_data.copy())
                if created:
                    inserted += 1
                else:
                    updated += 1
            except Exception:
                logger.exception(
                    "Failed to upsert item_seq=%s",
                    item_data.get("item_seq", "unknown"),
                )
                continue

            if idx % batch_size == 0:
                logger.info(
                    "Upsert progress: %d/%d (inserted=%d, updated=%d)",
                    idx,
                    total,
                    inserted,
                    updated,
                )

        logger.info(
            "Bulk upsert complete: total=%d, inserted=%d, updated=%d",
            total,
            inserted,
            updated,
        )
        return {"inserted": inserted, "updated": updated}

    async def get_last_sync_date(self) -> str | None:
        """Get the last successful sync date for medicine_info.

        Returns:
            Date string in YYYYMMDD format, or None if no sync recorded.
        """
        last_log = (
            await DataSyncLog
            .filter(
                sync_type="medicine_info",
                status="SUCCESS",
            )
            .order_by("-sync_date")
            .first()
        )

        if not last_log:
            return None
        return last_log.sync_date.strftime("%Y%m%d")

    async def count_all(self) -> int:
        """Count total medicine info records.

        Returns:
            Total number of records in medicine_info table.
        """
        return await MedicineInfo.all().count()
