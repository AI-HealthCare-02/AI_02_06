"""Medication API router module.

This module contains HTTP endpoints for medication operations
including creating, reading, updating, and deleting medications.
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
    """Get medication service instance.

    Returns:
        MedicationService: Medication service instance.
    """
    return MedicationService()


# Type aliases for dependency injection
MedicationServiceDep = Annotated[MedicationService, Depends(get_medication_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post(
    "",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register medication",
)
async def create_medication(
    data: MedicationCreate,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
) -> MedicationResponse:
    """Register a new medication.

    Args:
        data: Medication creation data.
        current_account: Current authenticated account.
        service: Medication service instance.

    Returns:
        MedicationResponse: Created medication information.
    """
    medication = await service.create_medication_with_owner_check(data.profile_id, current_account.id, data)
    return MedicationResponse.model_validate(medication)


@router.get(
    "",
    response_model=list[MedicationResponse],
    summary="List medications",
)
async def list_medications(
    current_account: CurrentAccount,
    service: MedicationServiceDep,
    profile_id: UUID | None = None,
    active_only: bool = False,
) -> list[MedicationResponse]:
    """List medications with optional filtering by profile.

    Args:
        current_account: Current authenticated account.
        service: Medication service instance.
        profile_id: Optional profile ID to filter by.
        active_only: Whether to return only active medications.

    Returns:
        List[MedicationResponse]: List of medications.
    """
    if profile_id:
        # Verify profile ownership and retrieve medications
        if active_only:
            medications = await service.get_active_medications_with_owner_check(profile_id, current_account.id)
        else:
            medications = await service.get_medications_by_profile_with_owner_check(profile_id, current_account.id)
    else:
        # Retrieve medications for all profiles of the account
        medications = await service.get_medications_by_account(current_account.id)
    return [MedicationResponse.model_validate(med) for med in medications]


@router.get(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="Get medication details",
)
async def get_medication(
    medication_id: UUID,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
) -> MedicationResponse:
    """Get detailed information about a specific medication.

    Args:
        medication_id: Medication ID to retrieve.
        current_account: Current authenticated account.
        service: Medication service instance.

    Returns:
        MedicationResponse: Medication details.
    """
    medication = await service.get_medication_with_owner_check(medication_id, current_account.id)
    return MedicationResponse.model_validate(medication)


@router.patch(
    "/{medication_id}",
    response_model=MedicationResponse,
    summary="Update medication",
)
async def update_medication(
    medication_id: UUID,
    data: MedicationUpdate,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
) -> MedicationResponse:
    """Update medication information.

    Args:
        medication_id: Medication ID to update.
        data: Medication update data.
        current_account: Current authenticated account.
        service: Medication service instance.

    Returns:
        MedicationResponse: Updated medication information.
    """
    medication = await service.update_medication_with_owner_check(medication_id, current_account.id, data)
    return MedicationResponse.model_validate(medication)


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete medication",
)
async def delete_medication(
    medication_id: UUID,
    current_account: CurrentAccount,
    service: MedicationServiceDep,
) -> None:
    """Delete a medication.

    Args:
        medication_id: Medication ID to delete.
        current_account: Current authenticated account.
        service: Medication service instance.
    """
    await service.delete_medication_with_owner_check(medication_id, current_account.id)
