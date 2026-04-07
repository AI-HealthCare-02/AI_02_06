"""
Medication Router

약품 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dtos.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["Medications"])


def get_medication_service() -> MedicationService:
    return MedicationService()


MedicationServiceDep = Annotated[MedicationService, Depends(get_medication_service)]


@router.post(
    "/",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="약품 등록",
)
async def create_medication(
    data: MedicationCreate,
    service: MedicationServiceDep,
):
    """새로운 약품을 등록합니다."""
    medication = await service.create_medication(data.profile_id, data)
    return MedicationResponse.model_validate(medication)


@router.get(
    "/",
    response_model=list[MedicationResponse],
    summary="약품 목록 조회",
)
async def list_medications(
    service: MedicationServiceDep,
    profile_id: UUID | None = None,
    active_only: bool = False,
):
    """약품 목록을 조회합니다. 프로필 ID로 필터링이 가능합니다."""
    if profile_id:
        if active_only:
            medications = await service.get_active_medications(profile_id)
        else:
            medications = await service.get_medications_by_profile(profile_id)
    else:
        from app.models.medication import Medication

        medications = await Medication.filter(deleted_at__isnull=True).all()
    return [MedicationResponse.model_validate(med) for med in medications]


@router.get(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="약품 상세 조회",
)
async def get_medication(
    medication_id: UUID,
    service: MedicationServiceDep,
):
    """특정 약품의 상세 정보를 조회합니다."""
    medication = await service.get_medication(medication_id)
    return MedicationResponse.model_validate(medication)


@router.patch(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="약품 정보 수정",
)
async def update_medication(
    medication_id: UUID,
    data: MedicationUpdate,
    service: MedicationServiceDep,
):
    """약품 정보를 수정합니다."""
    medication = await service.update_medication(medication_id, data)
    return MedicationResponse.model_validate(medication)


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="약품 삭제",
)
async def delete_medication(
    medication_id: UUID,
    service: MedicationServiceDep,
):
    """약품을 삭제합니다."""
    await service.delete_medication(medication_id)
    return None
