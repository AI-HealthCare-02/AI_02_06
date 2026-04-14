import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import redis.asyncio as redis  # 비동기 레디스 클라이언트 추가
import requests
from fastapi import UploadFile
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.dtos.ocr import ConfirmMedicationRequest, ExtractedMedicine, OcrExtractResponse

# DTO 경로 반영
from app.models.medication import Medication  # DB 모델 임포트

# 환경변수 우선, 없으면 OS 기본 임시 디렉토리 사용 (보안상 /tmp 하드코딩 방지)
_UPLOAD_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", tempfile.gettempdir())) / "ocr_images"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# LLM이 파싱 결과를 담아줄 내부 전용 Pydantic 모델
class LlmExtractionResult(BaseModel):
    medicines: list[ExtractedMedicine]


def _call_clova_ocr(image_path: Path) -> str:
    invoke_url = os.environ.get("CLOVA_OCR_INVOKE_URL")
    secret_key = os.environ.get("CLOVA_OCR_SECRET_KEY")
    if not invoke_url or not secret_key:
        raise ValueError("OCR 처리 실패: CLOVA_OCR 환경변수가 설정되지 않았습니다.")

    ext = image_path.suffix.lstrip(".").lower()
    request_json = {
        "images": [{"format": ext, "name": image_path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": int(round(time.time() * 1000)),
    }
    with open(image_path, "rb") as f:
        response = requests.post(
            invoke_url,
            headers={"X-OCR-SECRET": secret_key},
            data={"message": json.dumps(request_json).encode("UTF-8")},
            files=[("file", f)],
            timeout=30,
        )
    response.raise_for_status()
    fields = response.json()["images"][0]["fields"]
    return " ".join(field["inferText"] for field in fields)


class OCRService:
    def __init__(self) -> None:
        # Redis 연결 (환경변수로 URL 관리 권장)
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)

    async def extract_and_parse_image(self, file: UploadFile) -> OcrExtractResponse:
        # 1. 파일 임시 저장
        image_path = _UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        with image_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            # 2. Clova OCR 호출 (기존 _call_clova_ocr 함수 사용)
            raw_ocr_text = _call_clova_ocr(image_path)
            if not raw_ocr_text.strip():
                raise ValueError("이미지에서 텍스트를 추출할 수 없습니다.")

            # 3. LLM을 사용한 구조화 데이터 파싱 (Structured Outputs 적용)
            parsed_data = self._parse_text_with_llm(raw_ocr_text)

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

    def _parse_text_with_llm(self, text: str) -> LlmExtractionResult:
        """OCR 원문 텍스트를 LLM에 전달하여 정형화된 JSON 데이터로 파싱합니다."""
        prompt = f"""
        당신은 의료 데이터 파싱 전문가입니다. 다음 처방전(또는 약봉투) OCR 텍스트에서
        약품명과 복용 지시사항을 정확하게 추출하세요.

        [OCR 텍스트]
        {text}

        지침:
        1. 약품명(medicine_name)은 오탈자를 문맥에 맞게 보정하세요. (예: '타이레뉼' -> '타이레놀')
        2. 복용량, 횟수, 일수 등의 숫자를 정확히 분리하세요.
        3. 알 수 없는 필드는 null로 비워두세요.
        """
        try:
            # beta.chat.completions.parse를 사용하면 지정한 Pydantic 모델을 100% 보장하여 반환합니다.
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 일관성을 위해 낮게 설정
                response_format=LlmExtractionResult,
            )
            return response.choices[0].message.parsed
        except OpenAIError as e:
            raise ValueError(f"LLM 파싱 실패: {e}") from e

    async def get_draft_data(self, draft_id: str) -> OcrExtractResponse | None:
        """Redis에서 임시 저장된 데이터를 조회합니다."""
        data_json = await self.redis.get(f"ocr_draft:{draft_id}")
        if data_json:
            return OcrExtractResponse.model_validate_json(data_json)
        return None

    async def confirm_and_save(self, request: ConfirmMedicationRequest, profile_id: str) -> dict[str, Any]:
        """최종 데이터를 DB에 저장하고, 가이드를 생성한 뒤 Redis를 정리합니다."""
        saved_meds = []

        # 1. DB 영구 저장 (Tortoise ORM)
        for med in request.confirmed_medicines:
            # 복용 횟수 계산 로직 (기본값 처리)
            daily_count = med.daily_intake_count or 1
            total_days = med.total_intake_days or 1
            total_count = daily_count * total_days

            new_med = await Medication.create(
                profile_id=profile_id,
                medicine_name=med.medicine_name,
                dose_per_intake=med.dose_per_intake,
                intake_instruction=med.intake_instruction,
                daily_intake_count=daily_count,
                total_intake_days=total_days,
                intake_times=[],  # 초기값 (나중에 유저가 설정 기능 등 추가 가능)
                total_intake_count=total_count,
                remaining_intake_count=total_count,
                start_date=date.today(),
                is_active=True,
            )
            saved_meds.append(new_med)

        # 2. Redis 보안 데이터 파기
        # 처리가 끝났으므로 찌꺼기가 남지 않도록 즉시 삭제합니다.
        await self.redis.delete(f"ocr_draft:{request.draft_id}")

        # 3. LLM 기반 최종 복약 가이드 생성
        # DB JSON이 아니라 "사용자가 수정한 정확한 데이터"를 기반으로 작성합니다.
        guide = self._generate_final_guide(request.confirmed_medicines)

        return {
            "status": "success",
            "message": f"{len(saved_meds)}개의 약품이 성공적으로 저장되었습니다.",
            "guide": guide,
        }

    def _generate_final_guide(self, medicines: list[ExtractedMedicine]) -> str:
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
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 가이드 생성은 mini로도 충분히 훌륭합니다.
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or "가이드를 생성할 수 없습니다."
        except OpenAIError:
            return "약품은 정상적으로 저장되었으나, 복약 가이드를 생성하는 중 오류가 발생했습니다."
