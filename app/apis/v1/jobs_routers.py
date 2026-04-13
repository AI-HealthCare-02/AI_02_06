from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from rq.job import Job

from app.queues.rq import get_redis_connection

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="비동기 작업 상태 조회",
)
async def get_job_status(job_id: str):
    """
    RQ job 상태 및 결과를 조회합니다.
    """
    conn = get_redis_connection()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "job_not_found", "error_description": "작업을 찾을 수 없습니다.", "cause": str(e)},
        ) from e

    status_str = job.get_status()
    response = {
        "job_id": job.id,
        "status": status_str,
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
    }

    if status_str == "finished":
        response["result"] = job.result
    elif status_str == "failed":
        response["error"] = "job_failed"
        response["error_description"] = "작업 처리에 실패했습니다."
        response["exc_info"] = job.exc_info

    return response

