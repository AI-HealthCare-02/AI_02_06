"""OCR service module.

This module provides OCR (Optical Character Recognition) functionality
for processing prescription images and extracting medication information.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any
import uuid

from fastapi import BackgroundTasks, UploadFile
import httpx
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel
import redis.asyncio as redis

from app.core.config import config
from app.dtos.ocr import ConfirmMedicationRequest, ExtractedMedicine, OcrExtractResponse
from app.models.medication import Medication

# 공유 볼륨 경로 (Docker Compose의 ai-worker와 공유되어야 함)
_UPLOAD_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", tempfile.gettempdir())) / "ocr_images"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Internal Pydantic model for LLM parsing results
class LlmExtractionResult(BaseModel):
    """LLM extraction result model for structured OCR parsing.

    Attributes:
        medicines: List of extracted medicine information.
    """

    medicines: list[ExtractedMedicine]


async def _call_clova_ocr(image_path: Path) -> str:
    invoke_url = os.environ.get("CLOVA_OCR_INVOKE_URL")
    secret_key = os.environ.get("CLOVA_OCR_SECRET_KEY")
    if not invoke_url or not secret_key:
        raise ValueError("OCR processing failed: CLOVA_OCR environment variables not set.")

    ext = image_path.suffix.lstrip(".").lower()
    request_json = {
        "images": [{"format": ext, "name": image_path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": round(time.time() * 1000),
    }
    with image_path.open("rb") as f:
        image_data = f.read()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            invoke_url,
            headers={"X-OCR-SECRET": secret_key},
            data={"message": json.dumps(request_json).encode("UTF-8")},
            files=[("file", (image_path.name, image_data))],
        )
    response.raise_for_status()
    fields = response.json()["images"][0]["fields"]
    return " ".join(field["inferText"] for field in fields)


class OCRService:
    """OCR service for prescription image processing.

    This service handles OCR processing of prescription images,
    extracts medication information using LLM, and manages temporary data storage.
    """

    def __init__(self) -> None:
        # Redis 연결 (환경변수로 URL 관리 권장)
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=api_key)

    async def extract_and_parse_image(self, file: UploadFile) -> OcrExtractResponse:
        # 1. 파일 임시 저장
        image_path = _UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        with image_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            # 2. Clova OCR 호출
            raw_ocr_text = await _call_clova_ocr(image_path)
            if not raw_ocr_text.strip():
                raise ValueError("이미지에서 텍스트를 추출할 수 없습니다.")

            # 3. LLM을 사용한 구조화 데이터 파싱 (Structured Outputs 적용)
            parsed_data = await self._parse_text_with_llm(raw_ocr_text)

            if not parsed_data.medicines:
                raise ValueError("처방전에서 인식된 약 정보가 없습니다. 사진을 다시 찍어주세요.")

            # 4. Redis에 임시 저장 (10분 만료)
            draft_id = str(uuid.uuid4())
            response_obj = OcrExtractResponse(draft_id=draft_id, medicines=parsed_data.medicines)

            # Pydantic 모델을 JSON 문자열로 변환하여 Redis 저장
            await self.redis.setex(
                f"ocr_draft:{draft_id}",
                600,  # 600초 (10분)
                response_obj.model_dump_json(),
            )

            return response_obj

        finally:
            image_path.unlink(missing_ok=True)

    async def _parse_text_with_llm(self, text: str) -> LlmExtractionResult:
        """OCR 원문 텍스트를 LLM에 전달하여 정형화된 JSON 데이터로 파싱합니다."""
        prompt = f"""당신은 한국 처방전 데이터 파싱 전문가입니다. 아래 OCR 텍스트에서 약품 정보를 추출하세요.

[OCR 텍스트]
{text}

[추출 규칙]
1. medicine_name: 약품명 오탈자를 보정하세요. (예: '타이레뉼' -> '타이레놀')
2. dispensed_date: 처방전에 적힌 처방일(조제일)을 YYYY-MM-DD 형식으로 추출하세요. \
모든 약품에 동일하게 적용됩니다. 없으면 null.
3. department: 처방 진료과를 추출하세요. (예: '내과', '정형외과') 없으면 null.
4. category: 약품 분류를 추론하세요. (예: '해열진통제', '항생제', '소화제') 없으면 null.
5. dose_per_intake: 1회 복용량을 단위 포함하여 추출하세요. (예: '1정', '2캡슐', '5ml') 없으면 null.
6. daily_intake_count: 하루에 몇 번 복용하는지 정수로 추출하세요. (예: 1일 3회 -> 3) 없으면 null.
7. total_intake_days: 총 며칠간 복용하는지 정수로 추출하세요. (예: 5일치 -> 5) \
daily_intake_count와 다른 값입니다. 없으면 null.
8. intake_instruction: 복용 시점만 추출하세요. (예: '식후 30분', '취침 전', '공복') 없으면 null.

[중요] daily_intake_count(1일 횟수)와 total_intake_days(총 일수)는 반드시 다른 값입니다.
예시: "1일 3회 5일분" -> daily_intake_count=3, total_intake_days=5
알 수 없는 필드는 반드시 null로 설정하세요."""
        try:
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format=LlmExtractionResult,
            )
            return response.choices[0].message.parsed
        except OpenAIError as e:
            raise ValueError(f"LLM 파싱 실패: {e}") from e

    async def get_draft_data(self, draft_id: str) -> OcrExtractResponse | None:
        """Redis에서 워커가 완료한 데이터를 조회합니다 (Polling 대상)."""
        data_json = await self.redis.get(f"ocr_draft:{draft_id}")
        if data_json:
            return OcrExtractResponse.model_validate_json(data_json)
        return None

    async def confirm_and_save(
        self,
        request: ConfirmMedicationRequest,
        profile_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        """최종 데이터를 DB에 저장하고, 가이드를 생성한 뒤 Redis를 정리합니다."""
        saved_meds = []

        # 1. Redis 원자적 삭제 (중복 저장 방지 게이트)
        # delete()는 삭제된 키 개수를 반환합니다. 0이면 이미 처리된 요청입니다.
        deleted = await self.redis.delete(f"ocr_draft:{request.draft_id}")
        if deleted == 0:
            raise ValueError("이미 처리된 요청입니다. 새로 처방전을 등록해주세요.")

        # 2. DB 영구 저장 (Tortoise ORM)
        for med in request.confirmed_medicines:
            daily_count = med.daily_intake_count or 1
            total_days = med.total_intake_days or 1
            total_count = daily_count * total_days

            today = datetime.now(tz=config.TIMEZONE).date()
            new_med = await Medication.create(
                profile_id=profile_id,
                medicine_name=med.medicine_name,
                department=med.department,
                category=med.category,
                dose_per_intake=med.dose_per_intake,
                intake_instruction=med.intake_instruction,
                daily_intake_count=daily_count,
                total_intake_days=total_days,
                intake_times=[],  # TODO: 복용 시간 설정 기능 (다음 sprint)
                total_intake_count=total_count,
                remaining_intake_count=total_count,
                start_date=med.dispensed_date or today,
                dispensed_date=med.dispensed_date,
                is_active=True,
            )
            saved_meds.append(new_med)

        # 3. LLM 복약 가이드 생성은 백그라운드에서 비동기 처리 (응답 블로킹 방지)
        background_tasks.add_task(self._generate_final_guide, request.confirmed_medicines)

        return {
            "status": "success",
            "message": f"{len(saved_meds)}개의 약품이 성공적으로 저장되었습니다.",
        }

    async def _generate_final_guide(self, medicines: list[ExtractedMedicine]) -> str:
        """확정된 약품 리스트를 바탕으로 LLM을 호출하여 복약 가이드를 문자열로 만듭니다."""
        medicines_text = "\n".join(
            f"- {m.medicine_name} (1회 {m.dose_per_intake or '적정량'}, {m.intake_instruction or '지시대로 복용'})"
            for m in medicines
        )

        prompt = f"""당신은 친절하고 전문적인 약사 AI입니다.
        아래 환자가 복용할 최종 확정된 약물 리스트를 바탕으로 복약 가이드를 작성해주세요.

        [환자 복용 약물]
        {medicines_text}

        지침:
        1. 각 약품의 일반적인 효능과 주요 주의사항(졸음, 위장장애 등)을 알기 쉽게 설명하세요.
        2. 병용 금기나 주의해야 할 음식이 있다면 반드시 강조하세요.
        3. 문장은 부드럽고 격려하는 톤으로 작성하세요.
        4. 마지막에 반드시 다음 면책 문구를 포함하세요:
           "⚠️ 이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or "가이드를 생성할 수 없습니다."
        except OpenAIError:
            return "약품은 정상적으로 저장되었으나, 복약 가이드를 생성하는 중 오류가 발생했습니다."
