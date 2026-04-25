"""CLOVA OCR API 호출.

이미지 파일 1장을 받아 NAVER CLOVA OCR API 에 동기로 전송하고
``inferText`` 들을 공백으로 이어 붙인 단일 문자열을 반환한다.

본 모듈은 OCR 추출 단일 책임만 담당한다 — 텍스트 후처리는
``text_normalizer`` 가, 최종 약품 매칭은 ``medicine_matcher`` 가 맡는다.
"""

import json
import logging
from pathlib import Path
import time
import uuid

import httpx

from ai_worker.core.config import config

logger = logging.getLogger(__name__)

_OCR_TIMEOUT_SEC = 30.0


def extract_text_from_image(image_path: str) -> str:
    """CLOVA OCR API 를 호출해 이미지에서 추출된 텍스트를 반환한다.

    Args:
        image_path: OCR 처리할 이미지 절대 경로 (전처리 완료된 파일 권장).

    Returns:
        ``inferText`` 들을 공백으로 연결한 문자열. OCR 결과 없으면 빈 문자열.

    Raises:
        ValueError: CLOVA OCR 환경변수(URL/SECRET) 누락.
        httpx.HTTPStatusError: OCR API 가 4xx/5xx 응답.
    """
    invoke_url, secret_key = _resolve_credentials()
    payload = _build_request_payload(image_path)
    response_json = _post_to_clova(invoke_url, secret_key, image_path, payload)
    return _join_infer_texts(response_json)


def _resolve_credentials() -> tuple[str, str]:
    """CLOVA OCR URL / SECRET 환경변수를 검증·반환한다."""
    invoke_url = config.CLOVA_OCR_URL
    secret_key = config.CLOVA_OCR_SECRET
    if not invoke_url or not secret_key:
        raise ValueError("OCR 처리 실패: CLOVA_OCR 설정이 누락되었습니다.")
    return invoke_url, secret_key


def _build_request_payload(image_path: str) -> dict:
    """CLOVA OCR 요청 JSON payload 를 만든다."""
    path = Path(image_path)
    ext = path.suffix.lstrip(".").lower()
    return {
        "images": [{"format": ext, "name": path.stem}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": round(time.time() * 1000),
    }


def _post_to_clova(invoke_url: str, secret_key: str, image_path: str, payload: dict) -> dict:
    """CLOVA API 로 multipart POST 를 전송하고 JSON 응답을 반환한다."""
    path = Path(image_path)
    try:
        with path.open("rb") as f:
            response = httpx.post(
                invoke_url,
                headers={"X-OCR-SECRET": secret_key},
                data={"message": json.dumps(payload).encode("UTF-8")},
                files=[("file", f)],
                timeout=_OCR_TIMEOUT_SEC,
            )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError:
        logger.exception("CLOVA OCR API error for %s", image_path)
        raise
    except Exception:
        logger.exception("CLOVA OCR unexpected error for %s", image_path)
        raise


def _join_infer_texts(response_json: dict) -> str:
    """CLOVA 응답의 ``fields[].inferText`` 를 공백으로 이어 붙인다."""
    fields = response_json["images"][0]["fields"]
    return " ".join(field["inferText"] for field in fields)
