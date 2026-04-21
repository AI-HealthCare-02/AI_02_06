"""Medicine data synchronization service module.

This module provides business logic for fetching drug data from the
Food and Drug Safety public API and synchronizing it with the local
medicine_info database using incremental update strategy.

Reference:
    - API Docs: data.go.kr DrugPrdtPrmsnInfoService07 (2025)
    - Best Practice: data.go.kr bulk sync pattern with httpx pagination
"""

from datetime import UTC, datetime
import json
import logging
from pathlib import Path

import httpx

from app.models.data_sync_log import DataSyncLog
from app.repositories.medicine_info_repository import MedicineInfoRepository

logger = logging.getLogger(__name__)

# ── 공공데이터 API 설정 ──────────────────────────────────────────────
# 식약처 의약품 허가정보 서비스 (DrugPrdtPrmsnInfoService07)
_BASE_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07"
_DETAIL_ENDPOINT = f"{_BASE_URL}/getDrugPrdtPrmsnDtlInq06"  # 허가 상세정보

# ── 필터링 키워드 (병원 전용 주사제 제외, 자가주사는 유지) ────────────
_EXCLUDE_KEYWORDS = ("주사", "수액", "이식")
_SELF_INJECT_KEYWORDS = ("인슐린", "삭센다", "자가주사", "펜주", "프리필드")

# ── 백업 저장 경로 및 HTTP 설정 ──────────────────────────────────────
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "ai_worker" / "data"
_REQUEST_TIMEOUT = 30.0
_MAX_ROWS_PER_PAGE = 100


class MedicineDataService:
    """Service for public API drug data collection and synchronization.

    Handles full and incremental sync operations between
    the public API and the local medicine_info database.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.repository = MedicineInfoRepository()

    # ── 메인 동기화 메서드 ─────────────────────────────────────────
    # 전체 흐름:
    #   1. 파라미터 구성 (전체 or 증분)
    #   2. API 페이징 수집 (_fetch_all_pages)
    #   3. JSON 백업 저장 (_save_backup)
    #   4. 병원 전용 주사제 필터링 (_is_hospital_only_injectable)
    #   5. API 필드 -> 모델 필드 변환 (_transform_item)
    #   6. DB UPSERT (repository.bulk_upsert)
    #   7. 동기화 결과 로그 기록 (_record_sync_log)

    async def sync(self, full_sync: bool = False) -> dict[str, int]:
        """Execute full or incremental data synchronization.

        Args:
            full_sync: If True, fetches all records. If False,
                fetches only records changed since last sync.

        Returns:
            Dictionary with sync statistics.

        Raises:
            httpx.HTTPStatusError: If API request fails.
        """
        # Step 1: 전체/증분에 따라 API 요청 파라미터 구성
        params = self._build_params(full_sync)
        sync_start = datetime.now(tz=UTC)

        logger.info(
            "Starting %s sync for medicine_info",
            "full" if full_sync else "incremental",
        )

        # Step 2: API에서 전체 페이지 수집 (페이징 자동 처리)
        try:
            raw_items = await self._fetch_all_pages(params)
        except httpx.HTTPStatusError:
            await self._record_sync_log(
                sync_start,
                0,
                0,
                0,
                "FAILED",
                "API request failed",
            )
            raise

        if not raw_items:
            logger.info("No new data to sync")
            await self._record_sync_log(sync_start, 0, 0, 0, "SUCCESS")
            return {"fetched": 0, "inserted": 0, "updated": 0}

        # Step 3: 원본 데이터 JSON 백업 (감사 추적용)
        self._save_backup(raw_items)

        # Step 4: 병원 전용 주사제 필터링 (인슐린 등 자가주사는 유지)
        filtered = [item for item in raw_items if not self._is_hospital_only_injectable(item)]
        logger.info(
            "Filtered %d -> %d items (removed %d hospital-only injectables)",
            len(raw_items),
            len(filtered),
            len(raw_items) - len(filtered),
        )

        # Step 5-6: API 필드명 -> 모델 필드명 변환 후 DB UPSERT
        transformed = [self._transform_item(item) for item in filtered]
        stats = await self.repository.bulk_upsert(transformed)

        # Step 7: 동기화 결과를 data_sync_log 테이블에 기록
        await self._record_sync_log(
            sync_start,
            len(raw_items),
            stats["inserted"],
            stats["updated"],
            "SUCCESS",
        )

        logger.info(
            "Sync complete: fetched=%d, inserted=%d, updated=%d",
            len(raw_items),
            stats["inserted"],
            stats["updated"],
        )
        return {
            "fetched": len(raw_items),
            "inserted": stats["inserted"],
            "updated": stats["updated"],
        }

    # ── API 파라미터 구성 (전체: 필터 없음 / 증분: start_change_date 설정) ──

    async def _build_params(self, full_sync: bool) -> dict:
        """Build API request parameters for full or incremental sync.

        Args:
            full_sync: Whether to perform full sync.

        Returns:
            Dictionary of API request parameters.
        """
        params: dict = {
            "serviceKey": self.api_key,
            "type": "json",
            "numOfRows": _MAX_ROWS_PER_PAGE,
            "pageNo": 1,
        }

        if full_sync:
            return params

        last_date = await self.repository.get_last_sync_date()
        if last_date:
            params["start_change_date"] = last_date
            logger.info("Incremental sync from date: %s", last_date)
        else:
            logger.info("No previous sync found, falling back to full sync")

        return params

    # ── 페이징 수집 (pageNo를 증가시키며 totalCount에 도달할 때까지 반복) ──

    async def _fetch_all_pages(self, params: dict) -> list[dict]:
        """Fetch all pages of data from the public API.

        Paginates through API responses until all data is collected.

        Args:
            params: Base API request parameters.

        Returns:
            List of all item dictionaries from the API.
        """
        all_items: list[dict] = []

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            page = 1
            while True:
                params["pageNo"] = page
                response = await client.get(
                    _DETAIL_ENDPOINT,
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                body = data.get("body", {})
                items = body.get("items", [])

                if not items:
                    break

                all_items.extend(items)
                total_count = body.get("totalCount", 0)

                logger.info(
                    "Fetched page %d: %d items (total so far: %d/%d)",
                    page,
                    len(items),
                    len(all_items),
                    total_count,
                )

                if len(all_items) >= total_count:
                    break

                page += 1

        return all_items

    # ── 필터링: 병원 전용 주사제 판별 ──────────────────────────────

    @staticmethod
    def _is_hospital_only_injectable(item: dict) -> bool:
        """Check if the item is a hospital-only injectable drug.

        Excludes injectables, infusions, and implants but keeps
        self-injectable drugs like insulin and saxenda.

        Args:
            item: Raw API response item dictionary.

        Returns:
            True if the item should be excluded from consumer DB.
        """
        name = item.get("ITEM_NAME", "")
        has_exclude = any(kw in name for kw in _EXCLUDE_KEYWORDS)
        has_self_inject = any(kw in name for kw in _SELF_INJECT_KEYWORDS)
        return has_exclude and not has_self_inject

    # ── API 응답 필드 -> DB 모델 필드 매핑 변환 ────────────────────

    @staticmethod
    def _transform_item(item: dict) -> dict:
        """Transform raw API item to medicine_info model field format.

        Args:
            item: Raw API response item dictionary.

        Returns:
            Dictionary with model-compatible field names and values.
        """
        return {
            "item_seq": item.get("ITEM_SEQ", ""),
            "medicine_name": item.get("ITEM_NAME", ""),
            "item_eng_name": item.get("ITEM_ENG_NAME") or None,
            "entp_name": item.get("ENTP_NAME") or None,
            "product_type": item.get("PRDUCT_TYPE") or None,
            "spclty_pblc": item.get("SPCLTY_PBLC") or None,
            "permit_date": item.get("ITEM_PERMIT_DATE") or None,
            "cancel_name": item.get("CANCEL_NAME") or None,
            "main_item_ingr": item.get("MAIN_ITEM_INGR") or None,
            "storage_method": item.get("STORAGE_METHOD") or None,
            "edi_code": item.get("EDI_CODE") or None,
            "bizrno": item.get("BIZRNO") or None,
        }

    # ── 원본 데이터 JSON 백업 (ai_worker/data/에 타임스탬프 파일) ──

    @staticmethod
    def _save_backup(items: list[dict]) -> None:
        """Save raw API data as JSON backup file.

        Stores timestamped JSON file in ai_worker/data/ for audit trail.

        Args:
            items: Raw API response items to save.
        """
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        filepath = _DATA_DIR / f"medicines_{timestamp}.json"

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        logger.info("Saved backup: %s (%d items)", filepath, len(items))

    # ── 동기화 결과 로그 기록 (data_sync_log 테이블) ────────────────

    @staticmethod
    async def _record_sync_log(
        sync_date: datetime,
        total_fetched: int,
        total_inserted: int,
        total_updated: int,
        status: str,
        error_message: str | None = None,
    ) -> DataSyncLog:
        """Record sync operation result in DataSyncLog.

        Args:
            sync_date: When the sync started.
            total_fetched: Number of records fetched from API.
            total_inserted: Number of new records inserted.
            total_updated: Number of existing records updated.
            status: Sync result (SUCCESS or FAILED).
            error_message: Error details if status is FAILED.

        Returns:
            Created DataSyncLog instance.
        """
        return await DataSyncLog.create(
            sync_type="medicine_info",
            sync_date=sync_date,
            total_fetched=total_fetched,
            total_inserted=total_inserted,
            total_updated=total_updated,
            status=status,
            error_message=error_message,
        )
