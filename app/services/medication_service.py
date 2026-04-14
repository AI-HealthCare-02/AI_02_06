"""
Medication Service

약품 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.medication import MedicationCreate, MedicationUpdate
from app.models.medication import Medication
from app.repositories.medication_repository import MedicationRepository
from app.repositories.profile_repository import ProfileRepository


class MedicationService:
    """약품 비즈니스 로직"""

    def __init__(self):
        self.repository = MedicationRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """프로필 소유권 검증"""
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필을 찾을 수 없습니다.",
            )
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 프로필에 대한 접근 권한이 없습니다.",
            )

    async def _verify_medication_ownership(self, medication: Medication, account_id: UUID) -> None:
        """약품 소유권 검증 (프로필을 통해)"""
        await medication.fetch_related("profile")
        if medication.profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 약품에 대한 접근 권한이 없습니다.",
            )

    async def get_medication(self, medication_id: UUID) -> Medication:
        """약품 조회"""
        medication = await self.repository.get_by_id(medication_id)
        if not medication:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="약품을 찾을 수 없습니다.",
            )
        return medication

    async def get_medications_by_profile(self, profile_id: UUID) -> list[Medication]:
        """프로필의 모든 약품 조회"""
        return await self.repository.get_all_by_profile(profile_id)

    async def get_medications_by_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """소유권 검증 후 프로필의 모든 약품 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_all_by_profile(profile_id)

    async def get_active_medications(self, profile_id: UUID) -> list[Medication]:
        """프로필의 복용 중인 약품 조회"""
        return await self.repository.get_active_by_profile(profile_id)

    async def get_active_medications_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """소유권 검증 후 프로필의 복용 중인 약품 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_active_by_profile(profile_id)

    async def get_medications_by_account(self, account_id: UUID) -> list[Medication]:
        """계정의 모든 프로필에 해당하는 약품 조회"""
        profiles = await self.profile_repository.get_all_by_account(account_id)
        profile_ids = [p.id for p in profiles]
        return await self.repository.get_all_by_profiles(profile_ids)

    async def get_medication_with_owner_check(self, medication_id: UUID, account_id: UUID) -> Medication:
        """소유권 검증 후 약품 조회"""
        medication = await self.get_medication(medication_id)
        await self._verify_medication_ownership(medication, account_id)
        return medication

    async def create_medication(
        self,
        profile_id: UUID,
        data: MedicationCreate,
    ) -> Medication:
        """약품 생성"""
        return await self.repository.create(
            profile_id=profile_id,
            medicine_name=data.medicine_name,
            dose_per_intake=data.dose_per_intake,
            intake_instruction=data.intake_instruction,
            intake_times=data.intake_times,
            total_intake_count=data.total_intake_count,
            remaining_intake_count=data.remaining_intake_count or data.total_intake_count,
            start_date=data.start_date,
            end_date=data.end_date,
            dispensed_date=data.dispensed_date,
            expiration_date=data.expiration_date,
            prescription_image_url=data.prescription_image_url,
        )

    async def create_medication_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
        data: MedicationCreate,
    ) -> Medication:
        """소유권 검증 후 약품 생성"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_medication(profile_id, data)

    async def update_medication(
        self,
        medication_id: UUID,
        data: MedicationUpdate,
    ) -> Medication:
        """약품 수정"""
        medication = await self.get_medication(medication_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(medication, **update_data)

    async def update_medication_with_owner_check(
        self,
        medication_id: UUID,
        account_id: UUID,
        data: MedicationUpdate,
    ) -> Medication:
        """소유권 검증 후 약품 수정"""
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(medication, **update_data)

    async def deactivate_medication(self, medication_id: UUID) -> Medication:
        """약품 비활성화 (복용 중단)"""
        medication = await self.get_medication(medication_id)
        return await self.repository.update(medication, is_active=False)

    async def delete_medication(self, medication_id: UUID) -> None:
        """약품 삭제 (soft delete)"""
        medication = await self.get_medication(medication_id)
        await self.repository.soft_delete(medication)

    async def delete_medication_with_owner_check(self, medication_id: UUID, account_id: UUID) -> None:
        """소유권 검증 후 약품 삭제 (soft delete)"""
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        await self.repository.soft_delete(medication)
