"""
Medication Service

약품 관련 비즈니스 로직
"""

import hashlib
import json
import os
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAIError

from app.dtos.drug_info import DrugInfoResponse, DrugInteraction
from app.dtos.medication import MedicationCreate, MedicationUpdate
from app.models.llm_response_cache import LLMResponseCache
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

    async def get_inactive_medications_with_owner_check(self, profile_id: UUID, account_id: UUID) -> list[Medication]:
        """소유권 검증 후 프로필의 복용 완료된 약품 조회"""
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.repository.get_inactive_by_profile(profile_id)

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

    async def get_drug_info_with_owner_check(self, medication_id: UUID, account_id: UUID) -> DrugInfoResponse:
        """소유권 검증 후 LLM 기반 약품 정보(주의사항/부작용/상호작용) 반환. llm_response_cache로 비용 절감."""
        medication = await self.get_medication_with_owner_check(medication_id, account_id)
        return await self._get_drug_info(medication.medicine_name)

    async def _get_drug_info(self, medicine_name: str) -> DrugInfoResponse:
        """약품명 기반 LLM 호출. 캐시 히트 시 DB에서 반환, 미스 시 LLM 호출 후 30일 캐시 저장."""
        from datetime import datetime, timezone

        prompt_key = f"drug_info_v1:{medicine_name}"
        prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()

        # 캐시 조회
        cached = await LLMResponseCache.filter(
            prompt_hash=prompt_hash,
            expires_at__gte=datetime.now(tz=timezone.utc),
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
                severe_reaction_advice=data.get("severe_reaction_advice", "심한 부작용이 나타나면 즉시 복용을 중단하고 의사와 상담하세요."),
            )
        except (OpenAIError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=502, detail=f"약품 정보를 가져오는 데 실패했습니다: {e}") from e

        # 30일 캐시 저장
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
        await LLMResponseCache.create(
            prompt_hash=prompt_hash,
            prompt_text=prompt_key,
            response=drug_info.model_dump(),
            expires_at=expires_at,
        )

        return drug_info
