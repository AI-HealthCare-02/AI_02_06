from pathlib import Path
from typing import Any

from .utils.chunker import DataChunker
from .utils.ocr import OCRError, call_clova_ocr, extract_medicine_names, extract_text_from_ocr
from .utils.rag import RAGGenerator

_MEDICINES_PATH = Path(__file__).parent / "data" / "medicines.json"


class MedicationGuideService:
    def __init__(self) -> None:
        self.medicine_db: list[dict[str, Any]] = DataChunker.load_json(str(_MEDICINES_PATH))
        self.rag = RAGGenerator()

    async def process(self, image_path: str) -> str:
        try:
            ocr_result = call_clova_ocr(image_path)
        except (OCRError, FileNotFoundError) as e:
            raise ValueError(f"OCR 처리 실패: {e}") from e

        ocr_text = extract_text_from_ocr(ocr_result)
        if not ocr_text.strip():
            raise ValueError("이미지에서 텍스트를 추출할 수 없습니다.")

        matched = extract_medicine_names(ocr_text, self.medicine_db)
        if not matched:
            raise ValueError("처방전에서 인식된 약 정보가 없습니다. 사진을 다시 찍어주세요.")

        chunks = DataChunker.json_to_chunks(matched)
        return await self.rag.generate_guide(matched, chunks)
