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

    medicine_name: str = Field(description="Extracted medicine name (e.g., Tylenol 500mg)")
    dose_per_intake: str | None = Field(None, description="Dose per intake (e.g., 1 tablet, 5ml)")
    daily_intake_count: int | None = Field(None, description="Daily intake frequency (e.g., 3)")
    total_intake_days: int | None = Field(None, description="Total intake days (e.g., 5)")
    intake_instruction: str | None = Field(None, description="Intake instructions (e.g., 30 minutes after meal)")


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
