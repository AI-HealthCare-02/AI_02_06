import json
from pathlib import Path
import time
import uuid

from openai import OpenAI
from pydantic import BaseModel
import redis
import requests

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger
from app.dtos.ocr import ExtractedMedicine, OcrExtractResponse

logger = get_logger(__name__)


# LLM 파싱용 내부 모델
class LlmExtractionResult(BaseModel):
    medicines: list[ExtractedMedicine]


def _call_clova_ocr(image_path: str) -> str:
    """Clova OCR API 호출 (워커 내부용)"""
    invoke_url = config.CLOVA_OCR_URL
    secret_key = config.CLOVA_OCR_SECRET

    if not invoke_url or not secret_key:
        raise ValueError("OCR 처리 실패: CLOVA_OCR 설정이 누락되었습니다.")

    path = Path(image_path)
    ext = path.suffix.lstrip(".").lower()

    request_json = {
        "images": [{"format": ext, "name": path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": round(time.time() * 1000),
    }

    try:
        with path.open("rb") as f:
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
    except Exception as e:
        logger.error(f"Clova OCR Error: {e}")
        raise


def _parse_text_with_llm(text: str, client: OpenAI) -> LlmExtractionResult:
    """LLM을 이용한 구조화 데이터 파싱 (워커 내부용)"""
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
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format=LlmExtractionResult,
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"LLM Parsing Error: {e}")
        raise


def process_ocr_task(image_path: str, draft_id: str) -> bool:
    """[RQ Task] OCR 추출 및 파싱 전체 프로세스. 결과를 Redis의 'ocr_draft:{draft_id}' 키에 저장합니다."""
    logger.info(f"Starting OCR task: {image_path} (Draft ID: {draft_id})")

    # Redis 연결 (동기 방식)
    redis_conn = redis.from_url(config.REDIS_URL, decode_responses=True)

    try:
        # 1. OCR 호출
        raw_text = _call_clova_ocr(image_path)
        if not raw_text.strip():
            raise ValueError("No text extracted from image")  # noqa: TRY301

        # 2. LLM 파싱
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        parsed_data = _parse_text_with_llm(raw_text, client)

        # 3. 결과 저장 (10분 만료)
        response_obj = OcrExtractResponse(draft_id=draft_id, medicines=parsed_data.medicines)

        redis_conn.setex(f"ocr_draft:{draft_id}", 600, response_obj.model_dump_json())

        logger.info(f"Successfully processed OCR task for {draft_id}")
        return True

    except Exception as e:
        logger.error(f"Task failed for {draft_id}: {e}")
        # 실패 상태를 명시적으로 저장 (선택 사항)
        redis_conn.setex(f"ocr_status:{draft_id}", 600, "failed")
        return False
    finally:
        # 임시 이미지 삭제
        Path(image_path).unlink(missing_ok=True)


def generate_guide_task(medicines_json: str, profile_id: str, job_id: str) -> bool:
    """[RQ Task] 최종 복약 가이드 생성 (비동기)."""
    logger.info(f"Starting Guide Generation task for Profile: {profile_id}")

    redis_conn = redis.from_url(config.REDIS_URL, decode_responses=True)
    medicines = json.loads(medicines_json)

    medicines_text = "\n".join(
        f"- {m['medicine_name']} "
        f"(1회 {m.get('dose_per_intake') or '적정량'}, "
        f"{m.get('intake_instruction') or '지시대로 복용'})"
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
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        guide = response.choices[0].message.content or "가이드를 생성할 수 없습니다."

        # 가이드 결과를 Redis에 저장 (사용자가 폴링해서 가져감)
        redis_conn.setex(f"ocr_guide:{job_id}", 600, guide)
        logger.info(f"Successfully generated guide for {job_id}")
        return True
    except Exception as e:
        logger.error(f"Guide Generation Task failed: {e}")
        return False
