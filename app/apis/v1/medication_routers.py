"""
Medication Router

약품 관련 HTTP 엔드포인트
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_current_account
from app.dtos.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from app.models.accounts import Account
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["Medications"])


def get_medication_service() -> MedicationService:
    return MedicationService()


MedicationServiceDep = Annotated[MedicationService, Depends(get_medication_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="약품 등록",
)
async def create_medication(
    data: MedicationCreate,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
):
    """새로운 약품을 등록합니다."""
    medication = await service.create_medication_with_owner_check(data.profile_id, current_account.id, data)
    return MedicationResponse.model_validate(medication)


@router.get(
    "",
    response_model=list[MedicationResponse],
    summary="약품 목록 조회",
)
async def list_medications(
    current_account: CurrentAccount,
    service: MedicationServiceDep,
    profile_id: UUID | None = None,
    active_only: bool = False,
):
    """약품 목록을 조회합니다. 프로필 ID로 필터링이 가능합니다."""
    if profile_id:
        # 프로필 소유권 검증 후 조회
        if active_only:
            medications = await service.get_active_medications_with_owner_check(profile_id, current_account.id)
        else:
            medications = await service.get_medications_by_profile_with_owner_check(profile_id, current_account.id)
    else:
        # 계정의 모든 프로필에 해당하는 약품 조회
        medications = await service.get_medications_by_account(current_account.id)
    return [MedicationResponse.model_validate(med) for med in medications]


@router.get(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="약품 상세 조회",
)
async def get_medication(
    medication_id: UUID,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
):
    """특정 약품의 상세 정보를 조회합니다."""
    medication = await service.get_medication_with_owner_check(medication_id, current_account.id)
    return MedicationResponse.model_validate(medication)


@router.patch(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="약품 정보 수정",
)
async def update_medication(
    medication_id: UUID,
    data: MedicationUpdate,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
):
    """약품 정보를 수정합니다."""
    medication = await service.update_medication_with_owner_check(medication_id, current_account.id, data)
    return MedicationResponse.model_validate(medication)


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="약품 삭제",
)
async def delete_medication(
    medication_id: UUID,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
):
    """약품을 삭제합니다."""
    await service.delete_medication_with_owner_check(medication_id, current_account.id)
    return None
