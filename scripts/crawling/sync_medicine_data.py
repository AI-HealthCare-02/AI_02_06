"""Medicine data synchronization CLI script.

Entry point for full or incremental synchronization of drug data
from the Food and Drug Safety public API (data.go.kr)
into the medicine_info database table.

Usage:
    # Full sync (first-time setup)
    python -m scripts.crawling.sync_medicine_data --full

    # Incremental sync (monthly update)
    python -m scripts.crawling.sync_medicine_data

    # With custom API key
    python -m scripts.crawling.sync_medicine_data --api-key YOUR_KEY
"""

import argparse
import asyncio
import logging
import sys

from tortoise import Tortoise

from app.core.config import config
from app.db.databases import TORTOISE_ORM
from app.services.medicine_data_service import MedicineDataService

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Sync medicine data from public API to database",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Perform full sync (default: incremental)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Public data API key (default: from .env)",
    )
    return parser.parse_args()


async def run_sync(full_sync: bool, api_key: str) -> None:
    """Initialize DB connection and run sync operation.

    Args:
        full_sync: Whether to perform full or incremental sync.
        api_key: Public data API key for authentication.
    """
    await Tortoise.init(config=TORTOISE_ORM)
    logger.info("Database connection established")

    try:
        service = MedicineDataService(api_key=api_key)
        stats = await service.sync(full_sync=full_sync)

        logger.info(
            "Sync result: fetched=%d, inserted=%d, updated=%d",
            stats["fetched"],
            stats["inserted"],
            stats["updated"],
        )
    finally:
        await Tortoise.close_connections()
        logger.info("Database connection closed")


def main() -> None:
    """CLI entry point for medicine data synchronization."""
    args = parse_args()

    api_key = args.api_key or config.DATA_GO_KR_API_KEY
    if not api_key:
        logger.error("API key is required. Set DATA_GO_KR_API_KEY in .env or pass --api-key argument.")
        sys.exit(1)

    sync_type = "full" if args.full else "incremental"
    logger.info("Starting %s medicine data sync", sync_type)

    asyncio.run(run_sync(full_sync=args.full, api_key=api_key))


if __name__ == "__main__":
    main()
