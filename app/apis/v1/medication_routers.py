from uuid import UUID

from fastapi import APIRouter, status

from app.dtos.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from app.models.medication import Medication
from app.utils.common import get_object_or_404

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.post("/", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(data: MedicationCreate):
    new_medication = await Medication.create(**data.model_dump())
    return MedicationResponse.model_validate(new_medication)


@router.get("/", response_model=list[MedicationResponse])
async def list_medications():
    medications = await Medication.all()
    return [MedicationResponse.model_validate(med) for med in medications]


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(medication_id: UUID):
    medication = await get_object_or_404(Medication, id=medication_id)
    return MedicationResponse.model_validate(medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(medication_id: UUID, data: MedicationUpdate):
    medication = await get_object_or_404(Medication, id=medication_id)

    update_data = data.model_dump(exclude_unset=True)
    await medication.update_from_dict(update_data).save()
    return MedicationResponse.model_validate(medication)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(medication_id: UUID):
    medication = await get_object_or_404(Medication, id=medication_id)
    await medication.delete()
    return None
