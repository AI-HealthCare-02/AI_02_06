from pydantic import BaseModel, Field


# 1. 개별 약품 추출 데이터 모델
class ExtractedMedicine(BaseModel):
    medicine_name: str = Field(description="추출된 약품명 (예: 타이레놀정500mg)")
    department: str | None = Field(None, description="처방 진료과 (예: 내과, 정형외과)")
    category: str | None = Field(None, description="약품 분류 (예: 해열진통제, 항생제)")
    dose_per_intake: str | None = Field(None, description="1회 복용량 단위 포함 (예: 1정, 2캡슐, 5ml)")
    daily_intake_count: int | None = Field(None, description="1일 복용 횟수 (예: 3)")
    total_intake_days: int | None = Field(None, description="총 복용 일수 (예: 5, daily_intake_count와 다른 값)")
    intake_instruction: str | None = Field(None, description="복용 시점 지시사항 (예: 식후 30분, 취침 전)")


# 2. OCR 추출 결과 응답 모델 (임시 저장소 기반)
class OcrExtractResponse(BaseModel):
    draft_id: str = Field(description="Redis에 임시 저장된 처방전 정보의 고유 ID")
    medicines: list[ExtractedMedicine]


# 3. 사용자 최종 확정 요청 모델
class ConfirmMedicationRequest(BaseModel):
    draft_id: str = Field(description="Redis 임시 저장 ID")
    confirmed_medicines: list[ExtractedMedicine]
