import asyncio
from pathlib import Path
from typing import Any

from app.services.ocr_service import OCRService


def run_ocr_from_path(image_path: str, original_filename: str | None = None) -> dict[str, Any]:
    """
    RQ task entrypoint (sync function).
    Runs the async OCR pipeline and cleans up the file afterwards.
    """
    path = Path(image_path)
    service = OCRService()
    try:
        return asyncio.run(service.extract_from_path(image_path=path, original_filename=original_filename))
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            # Best-effort cleanup; avoid failing the job due to cleanup issues.
            pass

