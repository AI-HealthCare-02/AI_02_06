"""
IntakeLog Router

복용 기록 관련 HTTP 엔드포인트
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dtos.intake_log import IntakeLogCreate, IntakeLogResponse
from app.services.intake_log_service import IntakeLogService

router = APIRouter(prefix="/intake-logs", tags=["Intake Logs"])


def get_intake_log_service() -> IntakeLogService:
    return IntakeLogService()


IntakeLogServiceDep = Annotated[IntakeLogService, Depends(get_intake_log_service)]


@router.post(
    "/",
    response_model=IntakeLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="복용 기록 생성",
)
async def create_intake_log(
    data: IntakeLogCreate,
    service: IntakeLogServiceDep,
):
    """새로운 복용 기록을 생성합니다."""
    intake_log = await service.create_intake_log(
        medication_id=data.medication_id,
        profile_id=data.profile_id,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
    )
    return IntakeLogResponse.model_validate(intake_log)


@router.get(
    "/",
    response_model=list[IntakeLogResponse],
    summary="복용 기록 목록 조회",
)
async def list_intake_logs(
    service: IntakeLogServiceDep,
    profile_id: UUID | None = None,
    target_date: date | None = None,
):
    """복용 기록 목록을 조회합니다."""
    if profile_id and target_date:
        logs = await service.get_logs_by_profile_and_date(profile_id, target_date)
    elif profile_id:
        logs = await service.get_today_logs(profile_id)
    else:
        from app.models.intake_log import IntakeLog

        logs = await IntakeLog.all()
    return [IntakeLogResponse.model_validate(log) for log in logs]


@router.get(
    "/{log_id}",
    response_model=IntakeLogResponse,
    summary="복용 기록 상세 조회",
)
async def get_intake_log(
    log_id: UUID,
    service: IntakeLogServiceDep,
):
    """특정 복용 기록의 상세 정보를 조회합니다."""
    intake_log = await service.get_intake_log(log_id)
    return IntakeLogResponse.model_validate(intake_log)


@router.post(
    "/{log_id}/take",
    response_model=IntakeLogResponse,
    summary="복용 완료 처리",
)
async def mark_as_taken(
    log_id: UUID,
    service: IntakeLogServiceDep,
):
    """복용을 완료 처리합니다."""
    intake_log = await service.mark_as_taken(log_id)
    return IntakeLogResponse.model_validate(intake_log)


@router.post(
    "/{log_id}/skip",
    response_model=IntakeLogResponse,
    summary="복용 스킵 처리",
)
async def mark_as_skipped(
    log_id: UUID,
    service: IntakeLogServiceDep,
):
    """복용을 스킵 처리합니다."""
    intake_log = await service.mark_as_skipped(log_id)
    return IntakeLogResponse.model_validate(intake_log)


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="복용 기록 삭제",
)
async def delete_intake_log(
    log_id: UUID,
    service: IntakeLogServiceDep,
):
    """복용 기록을 삭제합니다."""
    await service.delete_intake_log(log_id)
    return None
