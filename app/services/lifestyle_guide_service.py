"""Lifestyle guide service module.

This module provides business logic for generating personalized lifestyle
guides via LLM based on a user's active medication list.

Flow:
    active meds query → prompt build → GPT call → JSON parse →
    guide save → challenge bulk-create
"""

import logging
import os
from uuid import UUID

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.dtos.lifestyle_guide import LlmGuideResponse
from app.models.challenge import Challenge
from app.models.lifestyle_guide import LifestyleGuide
from app.models.medication import Medication
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.lifestyle_guide_repository import LifestyleGuideRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.lifestyle_guide_prompt_builder import build_guide_prompt

logger = logging.getLogger(__name__)

_LLM_MODEL = "gpt-4o-mini"
_LLM_TEMPERATURE = 0.3


def _med_to_dict(med: Medication) -> dict:
    """Serialize a Medication ORM object to a snapshot-safe dict.

    Args:
        med: Medication ORM instance.

    Returns:
        dict: Minimal serializable representation.
    """
    return {
        "medicine_name": med.medicine_name,
        "category": getattr(med, "category", None),
        "intake_instruction": getattr(med, "intake_instruction", None),
        "dose_per_intake": getattr(med, "dose_per_intake", None),
    }


class LifestyleGuideService:
    """Business logic service for lifestyle guide generation and retrieval."""

    def __init__(self) -> None:
        self.medication_repo = MedicationRepository()
        self.guide_repo = LifestyleGuideRepository()
        self.challenge_repo = ChallengeRepository()

        self.profile_repo = ProfileRepository()

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.llm_client = AsyncOpenAI(api_key=api_key)

    async def generate_guide(self, profile_id: UUID) -> LifestyleGuide:
        """Generate a personalized lifestyle guide for a profile.

        Queries active medications, builds a GPT prompt, calls the LLM,
        persists the guide, and bulk-creates recommended challenges.

        Args:
            profile_id: Target profile UUID.

        Returns:
            LifestyleGuide: Newly created guide instance.

        Raises:
            ValueError: If no active medications exist or LLM call/parse fails.
        """
        # 1. Query active medications
        meds = await self.medication_repo.get_active_by_profile(profile_id)
        if not meds:
            raise ValueError("활성 약물 목록이 비어 있습니다. 가이드를 생성하려면 복용 중인 약물이 필요합니다.")

        # 2. Serialize meds for prompt and snapshot
        med_dicts = [_med_to_dict(m) for m in meds]
        logger.info("[GUIDE] GPT 호출 시작 profile_id=%s 약물 수=%d", profile_id, len(meds))

        # 3. Build prompt
        prompt = build_guide_prompt(med_dicts)

        # 4. Call LLM
        raw_json = await self._call_llm(prompt)

        # 5. Parse and validate JSON response
        parsed = self._parse_llm_response(raw_json)

        # 6. Save guide (content = 5 categories only, without challenges)
        content = parsed.model_dump(exclude={"recommended_challenges"})
        guide = await self.guide_repo.create(
            profile_id=profile_id,
            content=content,
            medication_snapshot=med_dicts,
        )
        logger.info("[GUIDE] 가이드 저장 완료 guide_id=%s profile_id=%s", guide.id, profile_id)

        # 7. Bulk create recommended challenges (is_active=False by default)
        await self.challenge_repo.bulk_create_from_guide(
            guide_id=guide.id,
            profile_id=profile_id,
            challenges=parsed.recommended_challenges,
        )
        logger.info(
            "[CHALLENGE] 추천 챌린지 생성 완료 guide_id=%s 개수=%d",
            guide.id,
            len(parsed.recommended_challenges),
        )

        return guide

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        """Verify that the account owns the profile.

        Args:
            profile_id: Profile UUID to verify.
            account_id: Account UUID that should own the profile.

        Raises:
            HTTPException: 404 if profile not found, 403 if access denied.
        """
        profile = await self.profile_repo.get_by_id(profile_id)
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

    async def _verify_guide_ownership(self, guide: LifestyleGuide, account_id: UUID) -> None:
        """Verify that the account owns the guide's profile.

        Args:
            guide: LifestyleGuide ORM instance.
            account_id: Account UUID that should own the guide.

        Raises:
            HTTPException: 403 if access denied.
        """
        profile = await self.profile_repo.get_by_id(guide.profile_id)
        if not profile or profile.account_id != account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guide.",
            )

    async def generate_guide_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> LifestyleGuide:
        """Generate a guide after verifying profile ownership.

        Args:
            profile_id: Target profile UUID.
            account_id: Requesting account UUID.

        Returns:
            LifestyleGuide: Newly created guide.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.generate_guide(profile_id)

    async def get_guide_with_owner_check(
        self,
        guide_id: UUID,
        account_id: UUID,
    ) -> LifestyleGuide:
        """Get a guide by ID after verifying ownership.

        Args:
            guide_id: Guide UUID.
            account_id: Requesting account UUID.

        Returns:
            LifestyleGuide: Guide instance.

        Raises:
            HTTPException: 404 if not found, 403 if access denied.
        """
        guide = await self.guide_repo.get_by_id(guide_id)
        if not guide:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lifestyle guide not found.",
            )
        await self._verify_guide_ownership(guide, account_id)
        return guide

    async def get_latest_guide_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> LifestyleGuide:
        """Get the most recent guide for a profile after verifying ownership.

        Args:
            profile_id: Profile UUID.
            account_id: Requesting account UUID.

        Returns:
            LifestyleGuide: Latest guide instance.

        Raises:
            HTTPException: 404 if no guide exists, 403 if access denied.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        guide = await self.guide_repo.get_latest_by_profile(profile_id)
        if not guide:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No lifestyle guide found for this profile.",
            )
        return guide

    async def list_guides_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
    ) -> list[LifestyleGuide]:
        """List all guides for a profile after verifying ownership.

        Args:
            profile_id: Profile UUID.
            account_id: Requesting account UUID.

        Returns:
            list[LifestyleGuide]: Guides ordered newest first.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        return await self.guide_repo.get_all_by_profile(profile_id)

    async def delete_guide_with_owner_check(
        self,
        guide_id: UUID,
        account_id: UUID,
    ) -> None:
        """Delete a lifestyle guide after verifying ownership.

        Unstarted challenges (is_active=False) are soft-deleted.
        Active or completed challenges (is_active=True) are kept with guide_id=None.
        The guide itself is hard-deleted.

        Args:
            guide_id: Guide UUID to delete.
            account_id: Requesting account UUID.

        Raises:
            HTTPException: 404 if not found, 403 if access denied.
        """
        guide = await self.get_guide_with_owner_check(guide_id, account_id)
        challenges = await self.challenge_repo.get_by_guide_id(guide.id)

        for c in challenges:
            if not c.is_active:
                await self.challenge_repo.soft_delete(c)
            else:
                await Challenge.filter(id=c.id).update(guide_id=None)

        await self.guide_repo.delete_by_id(guide.id)
        logger.info("[GUIDE] 가이드 삭제 완료 guide_id=%s account_id=%s", guide_id, account_id)

    async def get_guide_challenges_with_owner_check(
        self,
        guide_id: UUID,
        account_id: UUID,
    ) -> list[Challenge]:
        """Get challenges linked to a guide after verifying ownership.

        Args:
            guide_id: Guide UUID.
            account_id: Requesting account UUID.

        Returns:
            list[Challenge]: Challenges generated from the guide.
        """
        guide = await self.guide_repo.get_by_id(guide_id)
        if not guide:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lifestyle guide not found.",
            )
        await self._verify_guide_ownership(guide, account_id)
        return await self.challenge_repo.get_by_guide_id(guide.id)

    async def _call_llm(self, prompt: str) -> str:
        """Call GPT and return the raw JSON string.

        Args:
            prompt: Formatted system prompt from build_guide_prompt.

        Returns:
            str: Raw JSON string from LLM response.

        Raises:
            ValueError: If OpenAI API call fails.
        """
        try:
            response = await self.llm_client.chat.completions.create(
                model=_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=_LLM_TEMPERATURE,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            logger.exception("[GUIDE] GPT 호출 실패")
            raise ValueError(f"가이드 생성 실패: LLM 호출 오류 — {e}") from e

    def _parse_llm_response(self, raw_json: str) -> LlmGuideResponse:
        """Validate and parse the LLM JSON string into a typed model.

        Args:
            raw_json: Raw JSON string from LLM.

        Returns:
            LlmGuideResponse: Validated guide response model.

        Raises:
            ValueError: If JSON is malformed or required fields are missing.
        """
        try:
            return LlmGuideResponse.model_validate_json(raw_json)
        except (ValidationError, ValueError) as e:
            logger.warning("[GUIDE] GPT 응답 파싱 실패 — %s", e)
            raise ValueError(f"가이드 생성 실패: LLM 응답 파싱 오류 — {e}") from e
