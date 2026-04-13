import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests

SUPPORTED_FORMATS = {"jpg", "jpeg", "png", "pdf", "tiff"}

# 허용할 기준 디렉토리 (프로젝트 루트 기준)
_ALLOWED_BASE_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", "/tmp/ocr_images")).resolve()


class OCRError(Exception):
    pass


def _resolve_safe_path(image_path: str) -> Path:
    """경로 탐색 공격 방지: 허용된 디렉토리 내 경로만 허용"""
    resolved = Path(image_path).resolve()
    if not str(resolved).startswith(str(_ALLOWED_BASE_DIR)):
        raise OCRError(f"허용되지 않은 경로입니다: {image_path}")
    return resolved


def call_clova_ocr(image_path: str) -> dict:
    invoke_url = os.environ.get("CLOVA_OCR_INVOKE_URL")
    secret_key = os.environ.get("CLOVA_OCR_SECRET_KEY")

    if not invoke_url or not secret_key:
        raise OCRError("CLOVA_OCR_INVOKE_URL 또는 CLOVA_OCR_SECRET_KEY 환경변수가 설정되지 않았습니다.")

    path = _resolve_safe_path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    ext = path.suffix.lstrip(".").lower()
    if ext not in SUPPORTED_FORMATS:
        raise OCRError(f"지원하지 않는 파일 형식입니다: {ext} (지원: {SUPPORTED_FORMATS})")

    request_json = {
        "images": [{"format": ext, "name": path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": int(round(time.time() * 1000)),
    }

    try:
        with open(path, "rb") as f:
            response = requests.post(
                invoke_url,
                headers={"X-OCR-SECRET": secret_key},
                data={"message": json.dumps(request_json).encode("UTF-8")},
                files=[("file", f)],
                timeout=30,
            )
        response.raise_for_status()
    except requests.Timeout as e:
        raise OCRError("CLOVA OCR 요청 시간이 초과되었습니다.") from e
    except requests.HTTPError as e:
        raise OCRError(f"CLOVA OCR API 오류: {e.response.status_code} - {e.response.text}") from e
    except requests.RequestException as e:
        raise OCRError(f"CLOVA OCR 요청 실패: {e}") from e

    return response.json()


def extract_text_from_ocr(ocr_result: dict) -> str:
    """CLOVA OCR 응답에서 전체 텍스트 추출"""
    try:
        fields = ocr_result["images"][0]["fields"]
        return " ".join(field["inferText"] for field in fields)
    except (KeyError, IndexError):
        return ""


def extract_medicine_names(ocr_text: str, drug_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OCR 텍스트에서 약품 리스트와 매칭되는 약품 반환"""
    return [drug for drug in drug_list if drug["name"] in ocr_text]
