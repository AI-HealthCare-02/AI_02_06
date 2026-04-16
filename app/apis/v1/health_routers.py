"""Health check endpoints module.

This module provides health check endpoints for monitoring application status,
including liveness and readiness probes for container orchestration.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint - liveness probe.

    Returns:
        Dict[str, str]: Health status response.
    """
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint - readiness probe.

    TODO: Add checks for DB connection, Redis connection, etc.

    Returns:
        Dict[str, str]: Readiness status response.
    """
    return {"status": "ready"}
