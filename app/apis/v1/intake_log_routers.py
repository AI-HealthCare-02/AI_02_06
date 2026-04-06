from uuid import UUID

from fastapi import APIRouter, status

from app.dtos.intake_log import IntakeLogCreate, IntakeLogResponse, IntakeLogUpdate
from app.models.intake_log import IntakeLog
from app.utils.common import get_object_or_404

router = APIRouter(prefix="/intake-logs", tags=["Intake Logs"])


@router.post("/", response_model=IntakeLogResponse, status_code=status.HTTP_201_CREATED)
async def create_intake_log(data: IntakeLogCreate):
    new_log = await IntakeLog.create(**data.model_dump())
    return IntakeLogResponse.model_validate(new_log)


@router.get("/", response_model=list[IntakeLogResponse])
async def list_intake_logs():
    logs = await IntakeLog.all()
    return [IntakeLogResponse.model_validate(log) for log in logs]


@router.get("/{log_id}", response_model=IntakeLogResponse)
async def get_intake_log(log_id: UUID):
    log = await get_object_or_404(IntakeLog, id=log_id)
    return IntakeLogResponse.model_validate(log)


@router.patch("/{log_id}", response_model=IntakeLogResponse)
async def update_intake_log(log_id: UUID, data: IntakeLogUpdate):
    log = await get_object_or_404(IntakeLog, id=log_id)

    update_data = data.model_dump(exclude_unset=True)
    await log.update_from_dict(update_data).save()
    return IntakeLogResponse.model_validate(log)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intake_log(log_id: UUID):
    log = await get_object_or_404(IntakeLog, id=log_id)
    await log.delete()
    return None
