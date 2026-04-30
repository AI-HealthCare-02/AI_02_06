"""Prescription group DTO models module.

처방전 그룹 카드 / 정렬 / 검색 / drill-down 응답 스키마. 단계 2 의 라우터가
사용한다.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.dtos.medication import MedicationResponse


class PrescriptionGroupSort(StrEnum):
    """``GET /prescription-groups`` 의 정렬 기준 — 날짜 / 병원 이름."""

    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    HOSPITAL_ASC = "hospital_asc"
    HOSPITAL_DESC = "hospital_desc"


class PrescriptionGroupStatus(StrEnum):
    """탭 필터 — 그룹 안 medication 의 활성 상태에 따라 분류."""

    ALL = "all"
    ACTIVE = "active"  # 그룹 안 1개 이상 medication 이 is_active=True
    COMPLETED = "completed"  # 그룹의 모든 medication 이 is_active=False (or end_date 지남)


class PrescriptionGroupCard(BaseModel):
    """처방전 카드 list 응답 — drill-down 전 요약 뷰.

    카드에 표시할 메타 + 약 수만 포함. 약 list 는 ``GET /{group_id}`` drill-down
    에서 ``MedicationResponse`` 로 받는다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="처방전 그룹 ID")
    profile_id: UUID = Field(..., description="소유 프로필 ID")
    hospital_name: str | None = Field(None, description="처방전 발행 병원 이름")
    department: str | None = Field(None, description="처방 진료과")
    dispensed_date: date | None = Field(None, description="처방 조제일")
    source: str = Field(..., description="생성 경로 (OCR/MANUAL/MIGRATED)")
    created_at: datetime = Field(..., description="그룹 생성 시각")
    medications_count: int = Field(..., description="그룹에 속한 medication 수 (deleted 제외)")
    has_active_medication: bool = Field(
        ...,
        description="그룹 안 1개 이상 medication 이 is_active=True (= 복용 중)",
    )


class PrescriptionGroupUpdate(BaseModel):
    """처방전 그룹 부분 수정 요청 — hospital_name / department.

    dispensed_date 는 처방 사실의 핵심 메타라 수정을 막는다 (잘못 등록되었으면
    삭제 후 재등록 권장).
    """

    hospital_name: str | None = Field(None, max_length=128, description="처방전 발행 병원 이름")
    department: str | None = Field(None, max_length=64, description="처방 진료과 (예: 내과)")


class PrescriptionGroupDetail(BaseModel):
    """처방전 drill-down 응답 — 그룹 메타 + medication list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="처방전 그룹 ID")
    profile_id: UUID = Field(..., description="소유 프로필 ID")
    hospital_name: str | None = Field(None, description="처방전 발행 병원 이름")
    department: str | None = Field(None, description="처방 진료과")
    dispensed_date: date | None = Field(None, description="처방 조제일")
    source: str = Field(..., description="생성 경로 (OCR/MANUAL/MIGRATED)")
    created_at: datetime = Field(..., description="그룹 생성 시각")
    medications: list[MedicationResponse] = Field(
        default_factory=list,
        description="그룹에 속한 medication 들 (deleted 제외, medicine_name 가나다 정렬)",
    )
