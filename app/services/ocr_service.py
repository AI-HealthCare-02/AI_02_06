import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import UploadFile
from openai import AsyncOpenAI, OpenAIError

# 환경변수 우선, 없으면 OS 기본 임시 디렉토리 사용 (보안상 /tmp 하드코딩 방지)
_UPLOAD_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", tempfile.gettempdir())) / "ocr_images"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_MEDICINES_PATH = Path(__file__).parent.parent.parent / "ai_worker" / "data" / "medicines.json"


def _load_medicines() -> list[dict[str, Any]]:
    with open(_MEDICINES_PATH, encoding="utf-8") as f:
        return json.load(f)


async def _call_clova_ocr(image_path: Path) -> str:
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
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = await client.post(
                invoke_url,
                headers={"X-OCR-SECRET": secret_key},
                data={"message": json.dumps(request_json).encode("UTF-8")},
                files=files,
            )
        response.raise_for_status()
        fields = response.json()["images"][0]["fields"]
    return " ".join(field["inferText"] for field in fields)


async def _generate_guide(medicines: list[dict[str, Any]]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    env = os.environ.get("APP_ENV", "dev")
    model = "gpt-4o" if env == "prod" else "gpt-4o-mini"
    client = AsyncOpenAI(api_key=api_key)

    medicines_text = "\n".join(f"- {m['name']} ({m['ingredient']})" for m in medicines)
    context_chunks = []
    for m in medicines:
        context_chunks.append(
            f"약 이름: {m['name']}\n성분: {m['ingredient']}\n용도: {m['usage']}\n"
            f"면책사항: {m['disclaimer']}\n병용금기 약물: {', '.join(m['contraindicated_drugs'])}\n"
            f"금기 음식: {', '.join(m['contraindicated_foods'])}"
        )
    context_text = "\n---\n".join(context_chunks)

    prompt = f"""당신은 전문 약사 AI입니다. 아래 환자 복용 약물과 참고 데이터를 바탕으로
친절하고 상세한 복약 가이드를 작성해주세요.

[환자 복용 약물]
{medicines_text}

[참고 데이터]
{context_text}

지침:
1. 병용 금기 성분과 음식을 강조해서 알려주세요.
2. 복용 시 주의사항(면책사항)을 포함해주세요.
3. 마지막에 반드시 다음 문구를 포함하세요:
   "⚠️ 이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."
"""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except OpenAIError as e:
        raise ValueError(f"OpenAI API 호출 실패: {e}") from e


class OCRService:
    def __init__(self) -> None:
        self._medicines = _load_medicines()

    async def extract_text_from_image(self, file: UploadFile) -> dict[str, Any]:
        safe_name = Path(file.filename or "upload").name
        image_path = _UPLOAD_DIR / f"{uuid.uuid4()}_{safe_name}"
        with image_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            return await self.extract_from_path(image_path=image_path, original_filename=file.filename)
        finally:
            image_path.unlink(missing_ok=True)

    async def extract_from_path(self, image_path: Path, original_filename: str | None = None) -> dict[str, Any]:
        ocr_text = await _call_clova_ocr(image_path)
        if not ocr_text.strip():
            raise ValueError("이미지에서 텍스트를 추출할 수 없습니다.")

        matched = [m for m in self._medicines if m["name"] in ocr_text]
        if not matched:
            raise ValueError("처방전에서 인식된 약 정보가 없습니다. 사진을 다시 찍어주세요.")

        guide = await _generate_guide(matched)
        return {"status": "success", "filename": original_filename, "guide": guide}
