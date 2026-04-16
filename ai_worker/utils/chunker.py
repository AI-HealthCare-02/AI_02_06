"""Data chunking utility module.

This module provides functionality to load JSON data and convert it
into text chunks for RAG (Retrieval-Augmented Generation) processing.
Follows modern Python patterns with built-in types and clear documentation.
"""

import json
from pathlib import Path
from typing import Any


class DataChunker:
    """Utility class for processing medicine data into text chunks.

    This class provides static methods for loading JSON data and converting
    it into structured text chunks suitable for RAG processing.
    """

    @staticmethod
    def load_json(file_path: str) -> list[dict[str, Any]]:
        """Load JSON data from file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            list[dict[str, Any]]: Loaded JSON data as list of dictionaries.

        Raises:
            FileNotFoundError: If the JSON file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        path = Path(file_path).resolve()
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def json_to_chunks(medicine_data: list[dict[str, Any]]) -> list[str]:
        """Convert JSON object list to medicine-specific text chunks.

        Args:
            medicine_data: List of medicine dictionaries.

        Returns:
            list[str]: List of text chunks, one per medicine.
        """
        chunks = []
        for med in medicine_data:
            text = (
                f"Medicine name: {med['name']}\n"
                f"Ingredient: {med['ingredient']}\n"
                f"Usage: {med['usage']}\n"
                f"Disclaimer: {med['disclaimer']}\n"
                f"Contraindicated drugs: {', '.join(med['contraindicated_drugs'])}\n"
                f"Contraindicated foods: {', '.join(med['contraindicated_foods'])}"
            )
            chunks.append(text)
        return chunks

    @staticmethod
    def json_to_text(medicine_data: list[dict[str, Any]]) -> str:
        """Convert entire data to single string (for compatibility).

        Args:
            medicine_data: List of medicine dictionaries.

        Returns:
            str: Single string containing all medicine data.
        """
        return "\n---\n".join(DataChunker.json_to_chunks(medicine_data))
