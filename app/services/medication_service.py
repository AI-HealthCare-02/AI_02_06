"""Medication service module.

This module provides business logic for medication management operations
including creation, updates, and ownership verification.
"""

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from uuid import UUID

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAIError

from app.dtos.drug_info import DrugInfoResponse, DrugInteraction
from app.dtos.medication import MedicationCreate, MedicationUpdate, PrescriptionDateItem
from app.models.llm_response_cache import LLMResponseCache
from app.models.medication import Medication
from app.repositories.medication_repository import MedicationRepository
from app.repositories.profile_repository import ProfileRepository


class MedicationService:
    """Medication business logic service for prescription management."""

    def __init__(self) -> None:
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

    async def get_inactive_medications_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """Get completed or expired medications for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[Medication]: List of inactive medications if profile is owned by account.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_inactive_by_profile(profile_id)

    async def get_prescription_dates_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> list[PrescriptionDateItem]:
        """Get prescription date summary for a profile with ownership verification.

        Args:
            profile_id: Profile UUID.
            account_id: Account UUID for ownership check.

        Returns:
            list[PrescriptionDateItem]: Grouped prescription dates sorted by date descending.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_prescription_dates_by_profile(profile_id)

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

    async def decrement_and_deactivate_if_exhausted(self, medication: Medication) -> Medication:
        """Decrement remaining intake count and deactivate medication if exhausted.

        복용 완료 시 잔여 횟수를 1 감소시키고, 0이 되면 is_active=False로 자동 비활성화합니다.
        처방전 만료와는 별개로, 복용 횟수 소진 기준의 자동 종료 로직입니다.

        Args:
            medication: Medication to update.

        Returns:
            Medication: Updated medication. Deactivated if remaining count reaches zero.
        """
        medication = await self.repository.decrement_remaining_count(medication)
        # 잔여 횟수 0 도달 시 해당 처방전 비활성화 (더 이상 복용 기록 생성 안 됨)
        if medication.remaining_intake_count == 0:
            medication = await self.repository.update(medication, is_active=False)
        return medication

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

    async def get_drug_info_with_owner_check(self, medication_id: UUID, account_id: UUID) -> DrugInfoResponse:
        """Get LLM-based drug information with ownership verification.

        Returns warnings, side effects, and interactions from LLM, with DB cache to reduce costs.

        Args:
            medication_id: Medication UUID.
            account_id: Account UUID for ownership check.

        Returns:
            DrugInfoResponse: Drug information including warnings, side effects, and interactions.
        """
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        return await self._get_drug_info(medication.medicine_name)

    async def _get_drug_info(self, medicine_name: str) -> DrugInfoResponse:
        """Fetch drug information by name from LLM, with 30-day DB cache.

        Args:
            medicine_name: Name of the medication.

        Returns:
            DrugInfoResponse: Drug information from cache or LLM.

        Raises:
            HTTPException: If OPENAI_API_KEY is missing or LLM call fails.
        """
        prompt_key = f"drug_info_v1:{medicine_name}"
        prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()

        # 캐시 조회
        cached = await LLMResponseCache.filter(
            prompt_hash=prompt_hash,
            expires_at__gte=datetime.now(tz=UTC),
        ).first()
        if cached:
            await LLMResponseCache.filter(id=cached.id).update(hit_count=cached.hit_count + 1)
            return DrugInfoResponse.model_validate(cached.response)

        # LLM 호출
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY가 설정되지 않았습니다.")

        client = AsyncOpenAI(api_key=api_key)
        prompt = f"""당신은 한국 약사 전문가입니다. '{medicine_name}' 약품에 대해 아래 JSON 형식으로만 답변하세요.

{{
  "medicine_name": "{medicine_name}",
  "warnings": ["주의사항1", "주의사항2", ...],
  "side_effects": ["부작용1", "부작용2", ...],
  "interactions": [
    {{"drug": "상호작용약품명", "description": "설명"}},
    ...
  ],
  "severe_reaction_advice": "심각한 반응 시 조언 문장"
}}

규칙:
- warnings: 복용 전 확인할 주의사항 3~5개 (임산부, 노약자, 음식 등)
- side_effects: 주요 부작용 4~6개 (단어 형태, 예: "두통", "어지러움")
- interactions: 병용 주의 약물 2~3개
- 모든 내용은 한국어로 작성
- JSON 외 다른 텍스트 없이 JSON만 반환"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            drug_info = DrugInfoResponse(
                medicine_name=data.get("medicine_name", medicine_name),
                warnings=data.get("warnings", []),
                side_effects=data.get("side_effects", []),
                interactions=[DrugInteraction(**i) for i in data.get("interactions", [])],
                severe_reaction_advice=data.get(
                    "severe_reaction_advice",
                    "심한 부작용이 나타나면 즉시 복용을 중단하고 의사와 상담하세요.",
                ),
            )
        except (OpenAIError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=502, detail=f"약품 정보를 가져오는 데 실패했습니다: {e}") from e

        # 30일 캐시 저장
        expires_at = datetime.now(tz=UTC) + timedelta(days=30)
        await LLMResponseCache.create(
            prompt_hash=prompt_hash,
            prompt_text=prompt_key,
            response=drug_info.model_dump(),
            expires_at=expires_at,
        )

        return drug_info
