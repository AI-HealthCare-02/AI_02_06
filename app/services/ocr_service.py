import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from ai_worker.service import MedicationGuideService

_UPLOAD_DIR = Path("/tmp/ocr_images")
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_medication_service = MedicationGuideService()


class OCRService:
    async def extract_text_from_image(self, file: UploadFile) -> dict[str, Any]:
        image_path = _UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

        with image_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            guide = _medication_service.process(str(image_path))
            return {"status": "success", "filename": file.filename, "guide": guide}
        except ValueError as e:
            raise e
        finally:
            image_path.unlink(missing_ok=True)
