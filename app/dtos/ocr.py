"""OCR DTO models module.

This module contains data transfer objects for OCR (Optical Character Recognition)
operations including medicine extraction, temporary storage, and confirmation.
"""

from pydantic import BaseModel, Field


class ExtractedMedicine(BaseModel):
    """Individual medicine extraction data model.

    Represents structured data extracted from prescription images
    including dosage, frequency, and instruction information.
    """

    medicine_name: str = Field(description="추출된 약품명 (예: 타이레놀정500mg)")
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
    medicines: list[ExtractedMedicine]


class ConfirmMedicationRequest(BaseModel):
    """User final confirmation request model.

    Used when user confirms and potentially modifies
    the extracted medication data before final storage.
    """

    draft_id: str = Field(description="Redis temporary storage ID")
    confirmed_medicines: list[ExtractedMedicine]
