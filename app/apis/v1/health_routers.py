"""
Health Check Endpoints
"""

import os

import redis
from fastapi import APIRouter, HTTPException, status
from tortoise import Tortoise

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """기본 헬스체크 - liveness probe"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """준비 상태 체크 - readiness probe"""
    checks: dict[str, str] = {}

    # DB check (Tortoise connection)
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "fail"

    # Redis check (optional: only if configured)
    try:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            r = redis.from_url(redis_url, socket_timeout=2)
            r.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "skipped"
    except Exception:
        checks["redis"] = "fail"

    if checks.get("db") != "ok" or checks.get("redis") == "fail":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}
