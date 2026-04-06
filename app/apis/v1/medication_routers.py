from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dtos.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from app.models.medication import Medication

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
    medication = await Medication.get_or_none(id=medication_id)
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")
    return MedicationResponse.model_validate(medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(medication_id: UUID, data: MedicationUpdate):
    medication = await Medication.get_or_none(id=medication_id)
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(medication, key, value)
    await medication.save()
    return MedicationResponse.model_validate(medication)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(medication_id: UUID):
    medication = await Medication.get_or_none(id=medication_id)
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")
    await medication.delete()
    return None
