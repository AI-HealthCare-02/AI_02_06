"""Medication service module.

This module provides business logic for medication management operations
including creation, updates, and ownership verification.
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.medication import MedicationCreate, MedicationUpdate
from app.models.medication import Medication
from app.repositories.medication_repository import MedicationRepository
from app.repositories.profile_repository import ProfileRepository


class MedicationService:
    """Medication business logic service for prescription management."""

    def __init__(self):
        self.repository = MedicationRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """Verify profile ownership.

        Args:
            profile_id: Profile UUID to verify.
            account_id: Account UUID that should own the profile.

        Raises:
            HTTPException: If profile not found or access denied.
        """
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        if profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this profile.",
            )

    async def _verify_medication_ownership(self, medication: Medication, account_id: UUID) -> None:
        """Verify medication ownership through profile.

        Args:
            medication: Medication to verify ownership for.
            account_id: Account UUID that should own the medication.

        Raises:
            HTTPException: If access denied to medication.
        """
        await medication.fetch_related("profile")
        if medication.profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this medication.",
            )

    async def get_medication(self, medication_id: UUID) -> Medication:
        """Get medication by ID.

        Args:
            medication_id: Medication UUID.

        Returns:
            Medication: Medication object.

        Raises:
            HTTPException: If medication not found.
        """
        medication = await self.repository.get_by_id(medication_id)
        if not medication:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medication not found.",
            )
        return medication

    async def get_medications_by_profile(self, profile_id: UUID) -> list[Medication]:
        """Get all medications for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Medication]: List of medications.
        """
        return await self.repository.get_all_by_profile(profile_id)

    async def get_medications_by_profile_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """Get all medications for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[Medication]: List of medications if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_all_by_profile(profile_id)

    async def get_active_medications(self, profile_id: UUID) -> list[Medication]:
        """Get active medications for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            list[Medication]: List of active medications.
        """
        return await self.repository.get_active_by_profile(profile_id)

    async def get_active_medications_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """Get active medications for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[Medication]: List of active medications if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_active_by_profile(profile_id)

    async def get_medications_by_account(self, account_id: UUID) -> list[Medication]:
        """Get medications for all profiles of an account.

        Args:
            account_id: Account UUID.

        Returns:
            list[Medication]: List of medications for all account profiles.
        """
        profiles = await self.profile_repository.get_all_by_account(account_id)
        profile_ids = [p.id for p in profiles]
        return await self.repository.get_all_by_profiles(profile_ids)

    async def get_medication_with_owner_check(self, medication_id: UUID, account_id: UUID) -> Medication:
        """Get medication with ownership verification.

        Args:
            medication_id: Medication UUID.
            account_id: Account UUID for ownership check.

        Returns:
            Medication: Medication if owned by account.
        """
        medication = await self.get_medication(medication_id)
        await self._verify_medication_ownership(medication, account_id)
        return medication

    async def create_medication(
        self,
        profile_id: UUID,
        data: MedicationCreate,
    ) -> Medication:
        """Create new medication.

        Args:
            profile_id: Profile UUID.
            data: Medication creation data.

        Returns:
            Medication: Created medication.
        """
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
        """Create medication with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.
            data: Medication creation data.

        Returns:
            Medication: Created medication if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.create_medication(profile_id, data)

    async def update_medication(
        self,
        medication_id: UUID,
        data: MedicationUpdate,
    ) -> Medication:
        """Update medication.

        Args:
            medication_id: Medication UUID.
            data: Medication update data.

        Returns:
            Medication: Updated medication.
        """
        medication = await self.get_medication(medication_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(medication, **update_data)

    async def update_medication_with_owner_check(
        self,
        medication_id: UUID,
        account_id: UUID,
        data: MedicationUpdate,
    ) -> Medication:
        """Update medication with ownership verification.

        Args:
            medication_id: Medication UUID.
            account_id: Account UUID for ownership check.
            data: Medication update data.

        Returns:
            Medication: Updated medication if owned by account.
        """
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(medication, **update_data)

    async def deactivate_medication(self, medication_id: UUID) -> Medication:
        """Deactivate medication (stop taking).

        Args:
            medication_id: Medication UUID.

        Returns:
            Medication: Deactivated medication.
        """
        medication = await self.get_medication(medication_id)
        return await self.repository.update(medication, is_active=False)

    async def delete_medication(self, medication_id: UUID) -> None:
        """Delete medication (soft delete).

        Args:
            medication_id: Medication UUID to delete.
        """
        medication = await self.get_medication(medication_id)
        await self.repository.soft_delete(medication)

    async def delete_medication_with_owner_check(self, medication_id: UUID, account_id: UUID) -> None:
        """Delete medication with ownership verification (soft delete).

        Args:
            medication_id: Medication UUID to delete.
            account_id: Account UUID for ownership check.
        """
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        await self.repository.soft_delete(medication)
