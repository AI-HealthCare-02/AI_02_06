"""AI Worker medication guide service module.

This module provides the main service class for processing prescription images
and generating medication guidance using OCR and RAG technologies.
"""

from pathlib import Path
from typing import Any

from .utils.chunker import DataChunker
from .utils.ocr import OCRError, call_clova_ocr, extract_medicine_names, extract_text_from_ocr
from .utils.rag import RAGGenerator

_MEDICINES_PATH = Path(__file__).parent / "data" / "medicines.json"


class MedicationGuideService:
    """Service for processing prescription images and generating medication guides.

    This service integrates OCR processing, medicine matching, and RAG-based
    guide generation to provide comprehensive medication guidance.
    """

    def __init__(self) -> None:
        """Initialize the medication guide service.

        Loads the medicine database and initializes the RAG generator.
        """
        self.medicine_db: list[dict[str, Any]] = DataChunker.load_json(str(_MEDICINES_PATH))
        self.rag = RAGGenerator()

    def process(self, image_path: str) -> str:
        """Process prescription image and generate medication guide.

        Args:
            image_path: Path to the prescription image file.

        Returns:
            str: Generated medication guide text.

        Raises:
            ValueError: If OCR processing fails or no medicines are recognized.
        """
        try:
            ocr_result = call_clova_ocr(image_path)
        except (OCRError, FileNotFoundError) as e:
            raise ValueError(f"OCR processing failed: {e}") from e

        ocr_text = extract_text_from_ocr(ocr_result)
        if not ocr_text.strip():
            raise ValueError("Unable to extract text from image.")

        matched = extract_medicine_names(ocr_text, self.medicine_db)
        if not matched:
            raise ValueError("No recognized medicine information from prescription. Please take the photo again.")

        chunks = DataChunker.json_to_chunks(matched)
        return self.rag.generate_guide(matched, chunks)
