"""Tests for medicine_info RAG seeding pure helpers.

Covers deterministic helpers (chunk text, content hash, JSON load).
DB-touching batch flow is tested in test_rag_seeding_batch.py.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

from scripts.seed_rag_data import (
    build_chunk_text,
    compute_content_hash,
    load_medicines_json,
)


class TestChunkTextFormat:
    """Tests for chunk text generation from medicine dicts."""

    def test_build_chunk_text_with_all_fields(self) -> None:
        """Chunk text must embed every relevant field."""
        medicine = {
            "id": 1,
            "name": "타이레놀정 500mg",
            "ingredient": "아세트아미노펜",
            "disclaimer": "일일 최대 4,000mg 초과 금지",
            "contraindicated_drugs": ["간독성 유발 약물", "타 아세트아미노펜 제품"],
            "contraindicated_foods": ["술(알코올)"],
            "usage": "해열진통",
        }

        result = build_chunk_text(medicine)

        assert "[타이레놀정 500mg]" in result
        assert "주성분은 아세트아미노펜" in result
        assert "주된 용도는 해열진통" in result
        assert "일일 최대 4,000mg 초과 금지" in result
        assert "간독성 유발 약물" in result
        assert "타 아세트아미노펜 제품" in result
        assert "술(알코올)" in result

    def test_build_chunk_text_with_no_contraindications(self) -> None:
        """'해당 없음' contraindications must be rendered verbatim."""
        medicine = {
            "id": 26,
            "name": "후시딘",
            "ingredient": "퓨시드산",
            "disclaimer": "내성 방지를 위해 필요한 기간만",
            "contraindicated_drugs": ["해당 없음"],
            "contraindicated_foods": ["해당 없음"],
            "usage": "상처항생제",
        }

        result = build_chunk_text(medicine)

        assert "[후시딘]" in result
        assert "퓨시드산" in result
        assert "해당 없음" in result

    def test_build_chunk_text_with_multiple_contraindicated_drugs(self) -> None:
        """Multiple contraindicated items must be joined by comma + space."""
        medicine = {
            "id": 4,
            "name": "게보린정",
            "ingredient": "아세트아미노펜, 이소프로필안티피린",
            "disclaimer": "공복 복용 피할 것",
            "contraindicated_drugs": ["진정제", "다른 진통제"],
            "contraindicated_foods": ["술", "고카페인"],
            "usage": "강한 진통",
        }

        result = build_chunk_text(medicine)

        assert "진정제, 다른 진통제" in result
        assert "술, 고카페인" in result


class TestLoadMedicinesJson:
    """Tests for JSON file loading."""

    def test_load_medicines_json_success(self) -> None:
        """medicines.json must load and contain the 50 seeded entries."""
        medicines = load_medicines_json()

        assert isinstance(medicines, list)
        assert len(medicines) == 50
        assert medicines[0]["name"] == "타이레놀정 500mg"

    def test_load_medicines_json_structure(self) -> None:
        """Every entry must carry the required MedicineInfo-mapped keys."""
        medicines = load_medicines_json()

        required_keys = {
            "id",
            "name",
            "ingredient",
            "disclaimer",
            "contraindicated_drugs",
            "contraindicated_foods",
            "usage",
        }

        for medicine in medicines:
            assert required_keys.issubset(medicine.keys())

    def test_load_medicines_json_file_not_found(self) -> None:
        """Missing file must return an empty list, not raise."""
        with patch.object(Path, "exists", return_value=False):
            result = load_medicines_json(Path("/nonexistent/path.json"))
            assert result == []


class TestContentHash:
    """Tests for content hash computation."""

    def test_compute_content_hash(self) -> None:
        """Hash must match Python's stdlib SHA-256 hexdigest."""
        content = "테스트 컨텐츠"
        expected = hashlib.sha256(content.encode()).hexdigest()

        assert compute_content_hash(content) == expected

    def test_compute_content_hash_deterministic(self) -> None:
        """Same input must always yield the same hash."""
        content = "동일한 컨텐츠"
        assert compute_content_hash(content) == compute_content_hash(content)
