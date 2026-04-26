"""OCR DTO models module.

This module contains data transfer objects for OCR (Optical Character Recognition)
operations including medicine extraction, temporary storage, and confirmation.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class OcrDraftStatus(StrEnum):
    """OCR 처리 상태 (프론트 폴링 응답용).

    PENDING: ai-worker 가 처리 중. 프론트는 폴링을 계속한다.
    READY:   처리 완료. ``medicines`` 필드에 결과가 채워져 있다.
    NO_TEXT: OCR 결과에 텍스트가 없음 (블러·빈 이미지 등). 사용자에게 재촬영 안내.
    NO_CANDIDATES: 텍스트는 있지만 약품명 후보 추출 실패. 사용자에게 다른 이미지 안내.
    FAILED:  처리 중 예외 발생. 일반 에러 안내.
    """

    PENDING = "pending"
    READY = "ready"
    NO_TEXT = "no_text"
    NO_CANDIDATES = "no_candidates"
    FAILED = "failed"


class ExtractedMedicine(BaseModel):
    """Individual medicine extraction data model.

    Represents structured data extracted from prescription images
    including dosage, frequency, and instruction information.
    """

    medicine_name: str = Field(description="추출된 약품명 (예: 타이레놀정500mg)")
    dispensed_date: date | None = Field(None, description="처방전에 적힌 처방(조제)일 (예: 2026-04-13)")
    department: str | None = Field(None, description="처방 진료과 (예: 내과, 정형외과)")
    category: str | None = Field(None, description="약품 분류 (예: 해열진통제, 항생제)")
    dose_per_intake: str | None = Field(None, description="1회 복용량 단위 포함 (예: 1정, 2캡슐, 5ml)")
    daily_intake_count: int | None = Field(None, description="1일 복용 횟수 (예: 3)")
    total_intake_days: int | None = Field(None, description="총 복용 일수 (예: 5, daily_intake_count와 다른 값)")
    intake_instruction: str | None = Field(None, description="복용 시점 지시사항 (예: 식후 30분, 취침 전)")


class OcrExtractResponse(BaseModel):
    """OCR extraction result response model.

    Contains temporarily stored prescription information
    with Redis-based draft ID for security.
    """

    draft_id: str = Field(description="Unique ID for prescription info temporarily stored in Redis")
    medicines: list[ExtractedMedicine] = Field(default_factory=list)


class OcrDraftPollResponse(BaseModel):
    """폴링 응답 — 상태 + (READY 일 때만) medicines.

    프론트는 ``status`` 를 보고 흐름을 분기한다:
    - PENDING: 대기, 다시 폴링
    - READY: medicines 표시 후 사용자 검수 화면으로
    - NO_TEXT / NO_CANDIDATES / FAILED: 안내 메시지 + 재업로드 유도
    """

    draft_id: str
    status: OcrDraftStatus
    medicines: list[ExtractedMedicine] = Field(default_factory=list)


class ConfirmMedicationRequest(BaseModel):
    """User final confirmation request model.

    Used when user confirms and potentially modifies
    the extracted medication data before final storage.
    """

    draft_id: str = Field(description="Redis temporary storage ID")
    confirmed_medicines: list[ExtractedMedicine]
