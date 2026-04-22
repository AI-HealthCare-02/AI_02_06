"""APScheduler configuration and FastAPI lifespan integration.

Registers cron jobs:
  - 00:05 KST: generate today's IntakeLog records
  - 00:10 KST: deactivate and soft-delete expired medications
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.workers.intake_log_worker import generate_today_intake_logs
from app.workers.medication_worker import expire_medications

logger = logging.getLogger(__name__)

_KST = "Asia/Seoul"


@asynccontextmanager
async def scheduler_lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Manage APScheduler lifecycle within FastAPI lifespan.

    Starts the scheduler on application startup and shuts it down on exit.

    Args:
        _app: FastAPI application instance (unused, required by lifespan protocol).

    Yields:
        None
    """
    scheduler = AsyncIOScheduler(timezone=_KST)
    scheduler.add_job(generate_today_intake_logs, "cron", hour=0, minute=5, id="generate_intake_logs")
    scheduler.add_job(expire_medications, "cron", hour=0, minute=10, id="expire_medications")
    scheduler.start()
    logger.info("APScheduler started: generate_intake_logs@00:05, expire_medications@00:10 KST")

    yield

    scheduler.shutdown(wait=False)
    logger.info("APScheduler shutdown complete")
