"""Prescription group service — list / detail / 정렬 / 검색.

단계 2 의 ``/medication`` 페이지 (= 복용 가이드) 가 처방전 카드 단위로 노출
되도록 그룹 list + drill-down 을 제공한다. 정렬 / 검색 / 탭(status) 은
서로 독립적으로 결합 가능 (사용자 합의).
"""

from uuid import UUID

from fastapi import HTTPException, status

from app.dtos.medication import MedicationResponse
from app.dtos.prescription_group import (
    PrescriptionGroupCard,
    PrescriptionGroupDetail,
    PrescriptionGroupSort,
    PrescriptionGroupStatus,
)
from app.models.medication import Medication
from app.models.prescription_group import PrescriptionGroup
from app.repositories.prescription_group_repository import PrescriptionGroupRepository
from app.repositories.profile_repository import ProfileRepository


class PrescriptionGroupService:
    """처방전 그룹 list / drill-down 서비스."""

    def __init__(self) -> None:
        self.repository = PrescriptionGroupRepository()
        self.profile_repository = ProfileRepository()

    async def _verify_profile_ownership(self, profile_id: UUID, account_id: UUID) -> None:
        profile = await self.profile_repository.get_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        if profile.account_id != account_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this profile.")

    # ── 처방전 카드 list ─────────────────────────────────────────────────
    # 흐름: ownership 검증 -> 정렬/검색 query 빌드 -> 약 수 + active 여부 집계
    #       -> PrescriptionGroupCard list 반환
    async def list_groups_with_owner_check(
        self,
        profile_id: UUID,
        account_id: UUID,
        *,
        sort: PrescriptionGroupSort = PrescriptionGroupSort.DATE_DESC,
        search: str | None = None,
        status_filter: PrescriptionGroupStatus = PrescriptionGroupStatus.ALL,
    ) -> list[PrescriptionGroupCard]:
        """처방전 카드 list — ownership 검증 + 정렬 + 검색 + 상태 필터.

        Args:
            profile_id: 조회 대상 프로필 UUID.
            account_id: 요청 계정 UUID (ownership 검증).
            sort: 날짜/진료과 asc/desc.
            search: 약품 이름 검색 — 이 약을 포함하는 그룹만 반환.
            status_filter: ALL / ACTIVE / COMPLETED 탭.

        Returns:
            정렬·검색·필터된 처방전 카드 list.
        """
        await self._verify_profile_ownership(profile_id, account_id)
        groups = await self._fetch_filtered_groups(profile_id, sort, search)
        cards: list[PrescriptionGroupCard] = []
        for group in groups:
            if not await self._matches_status(group, status_filter):
                continue
            cards.append(await self._build_card(group, status_filter))
        return cards

    async def _fetch_filtered_groups(
        self,
        profile_id: UUID,
        sort: PrescriptionGroupSort,
        search: str | None,
    ) -> list[PrescriptionGroup]:
        """정렬 + 검색이 적용된 그룹 query 결과."""
        order_by = _ORDER_BY_MAP[sort]
        query = PrescriptionGroup.filter(
            profile_id=profile_id,
            deleted_at__isnull=True,
        )
        if search:
            # 약품 이름 검색 — 그 약을 포함하는 group 만 필터.
            # ILIKE 부분일치 (대소문자 무시), 한글도 정상 매칭.
            matching_group_ids = (
                await Medication
                .filter(
                    profile_id=profile_id,
                    deleted_at__isnull=True,
                    medicine_name__icontains=search,
                )
                .distinct()
                .values_list("prescription_group_id", flat=True)
            )
            matching_ids = [gid for gid in matching_group_ids if gid is not None]
            if not matching_ids:
                return []
            query = query.filter(id__in=matching_ids)
        return await query.order_by(*order_by).all()

    async def _build_card(
        self,
        group: PrescriptionGroup,
        _status_filter: PrescriptionGroupStatus,
    ) -> PrescriptionGroupCard:
        """그룹 한 개의 카드 view 빌드 — medication 수 + active 여부 집계."""
        meds_count = await Medication.filter(
            prescription_group_id=group.id,
            deleted_at__isnull=True,
        ).count()
        has_active = await Medication.filter(
            prescription_group_id=group.id,
            deleted_at__isnull=True,
            is_active=True,
        ).exists()
        return PrescriptionGroupCard(
            id=group.id,
            profile_id=group.profile_id,
            department=group.department,
            dispensed_date=group.dispensed_date,
            source=group.source,
            created_at=group.created_at,
            medications_count=meds_count,
            has_active_medication=has_active,
        )

    async def _matches_status(
        self,
        group: PrescriptionGroup,
        status_filter: PrescriptionGroupStatus,
    ) -> bool:
        """탭 필터 매칭 — ACTIVE: 1개 이상 active 약 / COMPLETED: 전부 비활성."""
        if status_filter == PrescriptionGroupStatus.ALL:
            return True
        has_active = await Medication.filter(
            prescription_group_id=group.id,
            deleted_at__isnull=True,
            is_active=True,
        ).exists()
        if status_filter == PrescriptionGroupStatus.ACTIVE:
            return has_active
        return not has_active

    # ── drill-down: 단일 그룹 + 약 list ──────────────────────────────────
    async def get_group_with_owner_check(
        self,
        group_id: UUID,
        account_id: UUID,
    ) -> PrescriptionGroupDetail:
        """단일 그룹 + 그 안의 medication list (medicine_name 가나다 정렬).

        Args:
            group_id: 처방전 그룹 UUID.
            account_id: 요청 계정 UUID (그룹의 profile 이 이 계정 소속인지 검증).

        Returns:
            그룹 메타 + medication list.

        Raises:
            HTTPException: 404/403.
        """
        group = await self.repository.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription group not found.")
        await self._verify_profile_ownership(group.profile_id, account_id)
        meds = (
            await Medication
            .filter(
                prescription_group_id=group.id,
                deleted_at__isnull=True,
            )
            .order_by("medicine_name", "id")
            .all()
        )
        return PrescriptionGroupDetail(
            id=group.id,
            profile_id=group.profile_id,
            department=group.department,
            dispensed_date=group.dispensed_date,
            source=group.source,
            created_at=group.created_at,
            medications=[MedicationResponse.model_validate(m) for m in meds],
        )


_ORDER_BY_MAP: dict[PrescriptionGroupSort, tuple[str, ...]] = {
    PrescriptionGroupSort.DATE_DESC: ("-dispensed_date", "-created_at"),
    PrescriptionGroupSort.DATE_ASC: ("dispensed_date", "created_at"),
    PrescriptionGroupSort.DEPARTMENT_ASC: ("department", "-dispensed_date"),
    PrescriptionGroupSort.DEPARTMENT_DESC: ("-department", "-dispensed_date"),
}
