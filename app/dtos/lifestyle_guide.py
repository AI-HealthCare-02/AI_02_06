"""Lifestyle guide DTO models module.

This module contains data transfer objects for lifestyle guide operations
including LLM response parsing and API request/response serialization.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── LLM response parsing schemas ───────────────────────────────────────────


class RecommendedChallenge(BaseModel):
    """Single LLM-recommended challenge item.

    Attributes:
        category: Lifestyle category (diet/sleep/exercise/symptom/interaction).
        title: Short challenge title (max 64 chars).
        description: Optional detailed description.
        target_days: Target number of days.
        difficulty: Difficulty label.
    """

    category: str
    title: str = Field(..., max_length=64)
    description: str | None = None
    target_days: int
    difficulty: str | None = None


class LlmGuideResponse(BaseModel):
    """Validated structure of the GPT guide JSON response.

    Used to parse and validate the raw JSON string returned by the LLM.
    Each category field holds the guide text for that category.
    recommended_challenges holds challenges to bulk-create in the DB.

    Attributes:
        diet: Diet and nutrition guidance.
        sleep: Sleep and circadian rhythm guidance.
        exercise: Exercise and activity guidance.
        symptom: Symptom monitoring guidance.
        interaction: Drug-lifestyle interaction guidance.
        recommended_challenges: List of recommended challenges.
    """

    diet: str
    sleep: str
    exercise: str
    symptom: str
    interaction: str
    recommended_challenges: list[RecommendedChallenge] = Field(default_factory=list)


# ── API response schemas ────────────────────────────────────────────────────


class LifestyleGuideResponse(BaseModel):
    """Lifestyle guide API response model.

    Attributes:
        id: Guide UUID.
        profile_id: Owner profile UUID.
        content: GPT-generated guide content (5 categories).
        medication_snapshot: Active medication list at generation time.
        created_at: Guide creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="가이드 ID")
    profile_id: UUID = Field(..., description="프로필 ID")
    content: dict = Field(..., description="5개 카테고리 가이드 내용")
    medication_snapshot: list = Field(..., description="가이드 생성 시점 활성 약물 목록")
    created_at: datetime = Field(..., description="가이드 생성 일시")


# ── Daily symptom log schemas ───────────────────────────────────────────────


class DailySymptomLogCreate(BaseModel):
    """Daily symptom log creation request model.

    Attributes:
        profile_id: Owner profile UUID.
        log_date: Date of the symptom report.
        symptoms: List of reported symptom strings.
        note: Optional free-text note.
    """

    profile_id: UUID = Field(..., description="프로필 ID")
    log_date: date = Field(..., description="증상 기록 날짜")
    symptoms: list[str] = Field(default_factory=list, description="증상 목록")
    note: str | None = Field(None, max_length=512, description="자유 메모")


class DailySymptomLogResponse(BaseModel):
    """Daily symptom log API response model.

    Attributes:
        id: Log UUID.
        profile_id: Owner profile UUID.
        log_date: Date of the symptom report.
        symptoms: List of reported symptom strings.
        note: Optional free-text note.
        created_at: Record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="기록 ID")
    profile_id: UUID = Field(..., description="프로필 ID")
    log_date: date = Field(..., description="증상 기록 날짜")
    symptoms: list[str] = Field(..., description="증상 목록")
    note: str | None = Field(None, description="자유 메모")
    created_at: datetime = Field(..., description="생성 일시")
