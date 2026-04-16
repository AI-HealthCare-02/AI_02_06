"""OCR utility module for processing prescription images.

This module provides functionality to call CLOVA OCR API,
extract text from OCR results, and match medicine names.
Follows modern Python security and error handling practices.
"""

import json
import os
from pathlib import Path
import time
from typing import Any
import uuid

import requests

# Supported image formats for OCR processing
SUPPORTED_FORMATS = {"jpg", "jpeg", "png", "pdf", "tiff"}

# Allowed base directory for image processing (project root based)
_ALLOWED_BASE_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", "/tmp/ocr_images")).resolve()


class OCRError(Exception):
    """Custom exception for OCR-related errors.

    Raised when OCR processing fails due to API errors,
    network issues, or invalid input data.
    """


def _resolve_safe_path(image_path: str) -> Path:
    """Prevent path traversal attacks by allowing only paths within allowed directory.

    Args:
        image_path: Path to the image file.

    Returns:
        Path: Resolved safe path.

    Raises:
        OCRError: If path is outside allowed directory.
    """
    resolved = Path(image_path).resolve()
    if not str(resolved).startswith(str(_ALLOWED_BASE_DIR)):
        raise OCRError(f"Unauthorized path: {image_path}")
    return resolved


def call_clova_ocr(image_path: str) -> dict[str, Any]:
    """Call CLOVA OCR API to extract text from image.

    Args:
        image_path: Path to the image file to process.

    Returns:
        dict[str, Any]: OCR result from CLOVA API.

    Raises:
        OCRError: If OCR processing fails.
        FileNotFoundError: If image file doesn't exist.
    """
    invoke_url = os.environ.get("CLOVA_OCR_INVOKE_URL")
    secret_key = os.environ.get("CLOVA_OCR_SECRET_KEY")

    if not invoke_url or not secret_key:
        raise OCRError("CLOVA_OCR_INVOKE_URL or CLOVA_OCR_SECRET_KEY environment variable not set.")

    path = _resolve_safe_path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    ext = path.suffix.lstrip(".").lower()
    if ext not in SUPPORTED_FORMATS:
        raise OCRError(f"Unsupported file format: {ext} (supported: {SUPPORTED_FORMATS})")

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
    except requests.Timeout as e:
        raise OCRError("CLOVA OCR request timeout.") from e
    except requests.HTTPError as e:
        error_msg = f"CLOVA OCR API error: {e.response.status_code} - {e.response.text}"
        raise OCRError(error_msg) from e
    except requests.RequestException as e:
        raise OCRError(f"CLOVA OCR request failed: {e}") from e

    return response.json()


def extract_text_from_ocr(ocr_result: dict[str, Any]) -> str:
    """Extract full text from CLOVA OCR response.

    Args:
        ocr_result: OCR result dictionary from CLOVA API.

    Returns:
        str: Extracted text from OCR result.
    """
    try:
        fields = ocr_result["images"][0]["fields"]
        return " ".join(field["inferText"] for field in fields)
    except (KeyError, IndexError):
        return ""


def extract_medicine_names(ocr_text: str, drug_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract medicines from OCR text that match the drug list.

    Args:
        ocr_text: Text extracted from OCR.
        drug_list: List of drug dictionaries to match against.

    Returns:
        list[dict[str, Any]]: List of matched drug dictionaries.
    """
    return [drug for drug in drug_list if drug["name"] in ocr_text]
