"""Tests for the medicine_info RAG seeding script.

Covers pure helpers (chunk text, content hash, JSON load, embedding
normalization) and the DB-touching `seed_medicine_to_db` flow mocked
against the MedicineInfo model.
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.seed_rag_data import (
    build_chunk_text,
    compute_content_hash,
    generate_embedding,
    load_medicines_json,
    seed_medicine_to_db,
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


class TestSeedMedicineToDb:
    """Tests for DB seeding with the MedicineInfo model (mocked)."""

    @pytest.mark.asyncio
    async def test_seed_medicine_creates_medicine_info_row(self) -> None:
        """Seeding must upsert a single MedicineInfo row per medicine."""
        medicine = {
            "id": 1,
            "name": "타이레놀정 500mg",
            "ingredient": "아세트아미노펜",
            "disclaimer": "일일 최대 4,000mg 초과 금지",
            "contraindicated_drugs": ["간독성 유발 약물"],
            "contraindicated_foods": ["술(알코올)"],
            "usage": "해열진통",
        }

        mock_embedding = [0.1] * 768

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=mock_embedding,
            ),
        ):
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=None)
            mock_model.filter = MagicMock(return_value=mock_filter)
            mock_model.create = AsyncMock()

            await seed_medicine_to_db(medicine)

            mock_model.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_medicine_stores_embedding_and_fields(self) -> None:
        """Seeding must pass the embedding and every medicine field to the model."""
        medicine = {
            "id": 2,
            "name": "까스활명수큐",
            "ingredient": "현삼, 육계, 정향",
            "disclaimer": "임부 및 수유부는 의사 상의 요망",
            "contraindicated_drugs": ["위장운동 조절제"],
            "contraindicated_foods": ["매운 음식", "탄산음료"],
            "usage": "소화불량",
        }

        mock_embedding = [0.5] * 768

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=mock_embedding,
            ),
        ):
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=None)
            mock_model.filter = MagicMock(return_value=mock_filter)
            mock_model.create = AsyncMock()

            await seed_medicine_to_db(medicine)

            kwargs = mock_model.create.call_args.kwargs
            assert kwargs["name"] == "까스활명수큐"
            assert kwargs["ingredient"] == "현삼, 육계, 정향"
            assert kwargs["usage"] == "소화불량"
            assert kwargs["disclaimer"] == "임부 및 수유부는 의사 상의 요망"
            assert kwargs["contraindicated_drugs"] == ["위장운동 조절제"]
            assert kwargs["contraindicated_foods"] == ["매운 음식", "탄산음료"]
            assert kwargs["embedding"] == mock_embedding
            assert kwargs["embedding_normalized"] is True
            assert len(kwargs["embedding"]) == 768

    @pytest.mark.asyncio
    async def test_seed_medicine_skips_existing(self) -> None:
        """Existing name must cause an early skip with no create call."""
        medicine = {
            "id": 1,
            "name": "타이레놀정 500mg",
            "ingredient": "아세트아미노펜",
            "disclaimer": "일일 최대 4,000mg 초과 금지",
            "contraindicated_drugs": ["간독성 유발 약물"],
            "contraindicated_foods": ["술(알코올)"],
            "usage": "해열진통",
        }

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1] * 768,
            ),
        ):
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=MagicMock())  # existing row
            mock_model.filter = MagicMock(return_value=mock_filter)
            mock_model.create = AsyncMock()

            await seed_medicine_to_db(medicine)

            mock_model.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_medicine_dry_run_does_not_touch_db(self) -> None:
        """`dry_run=True` must skip existence check and create call."""
        medicine = {
            "id": 3,
            "name": "아로나민 골드",
            "ingredient": "활성비타민 B군",
            "disclaimer": "뇨색 변색 가능성 있음",
            "contraindicated_drugs": ["레보도파"],
            "contraindicated_foods": ["차(탄닌 함유)"],
            "usage": "피로회복",
        }

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.2] * 768,
            ),
        ):
            mock_model.create = AsyncMock()
            mock_model.filter = MagicMock()

            await seed_medicine_to_db(medicine, dry_run=True)

            mock_model.create.assert_not_called()
            mock_model.filter.assert_not_called()


class TestEmbeddingGeneration:
    """Tests for embedding generation and L2 normalization."""

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_configured_dimensions(self) -> None:
        """Generated embedding length must match EMBEDDING_DIMENSIONS."""
        import numpy as np

        from app.services.rag.config import EMBEDDING_DIMENSIONS

        mock_embedding = np.array([0.1] * EMBEDDING_DIMENSIONS)

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=mock_embedding)
            mock_get_model.return_value = mock_model

            result = await generate_embedding("테스트 텍스트")

            assert len(result) == EMBEDDING_DIMENSIONS
            mock_model.encode.assert_called_once_with("테스트 텍스트")

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_normalized_vector(self) -> None:
        """Output vector must have L2 norm approximately 1."""
        import numpy as np

        mock_embedding = np.array([3.0, 4.0] + [0.0] * 766)

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=mock_embedding)
            mock_get_model.return_value = mock_model

            result = await generate_embedding("테스트 텍스트")

            norm = np.linalg.norm(result)
            assert abs(norm - 1.0) < 0.001
