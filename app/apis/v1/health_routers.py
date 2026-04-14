"""
Health Check Endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """기본 헬스체크 - liveness probe"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """준비 상태 체크 - readiness probe"""
    # TODO: DB 연결, Redis 연결 등 확인
    return {"status": "ready"}
