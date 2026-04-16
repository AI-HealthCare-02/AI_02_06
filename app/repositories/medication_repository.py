"""
Medication Repository

medications 테이블 데이터 접근 계층
"""

from datetime import date
from uuid import UUID, uuid4

from tortoise.expressions import Q

from app.models.medication import Medication


class MedicationRepository:
    """Medication DB 저장소"""

    async def get_by_id(self, medication_id: UUID) -> Medication | None:
        """약품 ID로 조회 (soft delete 제외)"""
        return await Medication.filter(
            id=medication_id,
            deleted_at__isnull=True,
        ).first()

    async def get_all_by_profile(self, profile_id: UUID) -> list[Medication]:
        """프로필의 모든 약품 조회"""
        return await Medication.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).all()

    async def get_all_by_profiles(self, profile_ids: list[UUID]) -> list[Medication]:
        """여러 프로필의 모든 약품 조회"""
        if not profile_ids:
            return []
        return await Medication.filter(
            profile_id__in=profile_ids,
            deleted_at__isnull=True,
        ).all()

    async def get_active_by_profile(self, profile_id: UUID) -> list[Medication]:
        """프로필의 복용 중인 약품 조회 (is_active=True이고 end_date가 오늘 이후인 것)"""
        today = date.today()
        return await Medication.filter(
            profile_id=profile_id,
            is_active=True,
            deleted_at__isnull=True,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).all()

    async def get_inactive_by_profile(self, profile_id: UUID) -> list[Medication]:
        """프로필의 복용 완료된 약품 조회 (수동 완료 처리 or end_date 경과)"""
        today = date.today()
        return await Medication.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        ).filter(
            Q(is_active=False) | Q(end_date__lt=today, end_date__isnull=False)
        ).all()

    async def create(
        self,
        profile_id: UUID,
        medicine_name: str,
        intake_times: list[str],
        total_intake_count: int,
        remaining_intake_count: int,
        start_date: date,
        dose_per_intake: str | None = None,
        intake_instruction: str | None = None,
        end_date: date | None = None,
        dispensed_date: date | None = None,
        expiration_date: date | None = None,
        prescription_image_url: str | None = None,
    ) -> Medication:
        """새 약품 생성"""
        return await Medication.create(
            id=uuid4(),
            profile_id=profile_id,
            medicine_name=medicine_name,
            dose_per_intake=dose_per_intake,
            intake_instruction=intake_instruction,
            intake_times=intake_times,
            total_intake_count=total_intake_count,
            remaining_intake_count=remaining_intake_count,
            start_date=start_date,
            end_date=end_date,
            dispensed_date=dispensed_date,
            expiration_date=expiration_date,
            prescription_image_url=prescription_image_url,
            is_active=True,
        )

    async def update(self, medication: Medication, **kwargs) -> Medication:
        """약품 정보 업데이트"""
        await medication.update_from_dict(kwargs).save()
        return medication

    async def soft_delete(self, medication: Medication) -> Medication:
        """약품 소프트 삭제"""
        from datetime import datetime

        from app.core import config

        medication.deleted_at = datetime.now(tz=config.TIMEZONE)
        await medication.save()
        return medication
