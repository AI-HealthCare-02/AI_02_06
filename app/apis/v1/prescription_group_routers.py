"""Prescription group API router — 카드 list + drill-down.

단계 2 의 ``/medication`` 페이지가 처방전 단위로 노출되도록 두 endpoint 만 제공:

1. ``GET /prescription-groups`` — 카드 list (정렬 + 검색 + 탭 결합)
2. ``GET /prescription-groups/{group_id}`` — 단일 그룹 drill-down (약 list 포함)
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies.security import get_current_account
from app.dtos.prescription_group import (
    PrescriptionGroupCard,
    PrescriptionGroupDetail,
    PrescriptionGroupSort,
    PrescriptionGroupStatus,
)
from app.models.accounts import Account
from app.services.prescription_group_service import PrescriptionGroupService

router = APIRouter(prefix="/prescription-groups", tags=["Prescription Groups"])


def get_prescription_group_service() -> PrescriptionGroupService:
    """PrescriptionGroupService 인스턴스 (DI)."""
    return PrescriptionGroupService()


PrescriptionGroupServiceDep = Annotated[PrescriptionGroupService, Depends(get_prescription_group_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get(
    "",
    response_model=list[PrescriptionGroupCard],
    summary="처방전 그룹 카드 list (정렬 + 검색 + 탭)",
)
async def list_prescription_groups(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: PrescriptionGroupServiceDep,
    sort: PrescriptionGroupSort = PrescriptionGroupSort.DATE_DESC,
    search: str | None = None,
    status_filter: PrescriptionGroupStatus = PrescriptionGroupStatus.ALL,
) -> list[PrescriptionGroupCard]:
    """처방전 카드 list — 정렬 / 검색 / 탭 결합.

    Args:
        profile_id: 조회 대상 프로필 UUID.
        current_account: 인증된 계정.
        service: PrescriptionGroupService 인스턴스.
        sort: ``date_desc`` (default) / ``date_asc`` / ``department_asc`` / ``department_desc``.
        search: 약품 이름 검색 — 이 약을 포함하는 그룹만 반환.
        status_filter: ``all`` (default) / ``active`` (복용 중) / ``completed`` (복용 완료).

    Returns:
        정렬·검색·필터된 처방전 카드 list.
    """
    return await service.list_groups_with_owner_check(
        profile_id,
        current_account.id,
        sort=sort,
        search=search,
        status_filter=status_filter,
    )


@router.get(
    "/{group_id}",
    response_model=PrescriptionGroupDetail,
    summary="처방전 그룹 drill-down (그룹 + 약 list)",
)
async def get_prescription_group(
    group_id: UUID,
    current_account: CurrentAccount,
    service: PrescriptionGroupServiceDep,
) -> PrescriptionGroupDetail:
    """단일 처방전 그룹 + 그 안의 medication list."""
    return await service.get_group_with_owner_check(group_id, current_account.id)
