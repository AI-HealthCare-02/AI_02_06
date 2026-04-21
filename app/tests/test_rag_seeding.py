"""RAG Seeding Script Tests.

This module contains tests for the RAG data seeding functionality
that loads medicines.json into pgvector database.
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.seed_rag_data import (
    build_chunk_text,
    compute_content_hash,
    load_medicines_json,
    seed_medicine_to_db,
)


class TestChunkTextFormat:
    """Tests for chunk text generation."""

    def test_build_chunk_text_with_all_fields(self) -> None:
        """Test chunk text format with all fields populated."""
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
        """Test chunk text with '해당 없음' contraindications."""
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
        """Test chunk text with multiple contraindicated drugs."""
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
        """Test successful loading of medicines.json."""
        medicines = load_medicines_json()

        assert isinstance(medicines, list)
        assert len(medicines) == 50
        assert medicines[0]["name"] == "타이레놀정 500mg"

    def test_load_medicines_json_structure(self) -> None:
        """Test that loaded JSON has correct structure."""
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
        """Test handling of missing JSON file."""
        with patch.object(Path, "exists", return_value=False):
            result = load_medicines_json(Path("/nonexistent/path.json"))
            assert result == []


class TestContentHash:
    """Tests for content hash computation."""

    def test_compute_content_hash(self) -> None:
        """Test content hash computation."""
        content = "테스트 컨텐츠"
        expected = hashlib.sha256(content.encode()).hexdigest()

        result = compute_content_hash(content)

        assert result == expected

    def test_compute_content_hash_deterministic(self) -> None:
        """Test that hash is deterministic."""
        content = "동일한 컨텐츠"

        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2


class TestSeedMedicineToDb:
    """Tests for database seeding logic."""

    @pytest.mark.asyncio
    async def test_seed_medicine_creates_document(self) -> None:
        """Test that seeding creates PharmaceuticalDocument."""
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
            patch("scripts.seed_rag_data.PharmaceuticalDocument") as mock_doc_cls,
            patch("scripts.seed_rag_data.DocumentChunk") as mock_chunk_cls,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=mock_embedding,
            ),
        ):
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc_cls.create = AsyncMock(return_value=mock_doc)
            mock_chunk_cls.create = AsyncMock()
            # Mock filter().first() chain for existence check
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=None)
            mock_chunk_cls.filter = MagicMock(return_value=mock_filter)

            await seed_medicine_to_db(medicine)

            mock_doc_cls.create.assert_called_once()
            mock_chunk_cls.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_medicine_creates_chunk_with_embedding(self) -> None:
        """Test that seeding creates DocumentChunk with embedding."""
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
            patch("scripts.seed_rag_data.PharmaceuticalDocument") as mock_doc_cls,
            patch("scripts.seed_rag_data.DocumentChunk") as mock_chunk_cls,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=mock_embedding,
            ),
        ):
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc_cls.create = AsyncMock(return_value=mock_doc)
            mock_chunk_cls.create = AsyncMock()
            # Mock filter().first() chain for existence check
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=None)
            mock_chunk_cls.filter = MagicMock(return_value=mock_filter)

            await seed_medicine_to_db(medicine)

            call_kwargs = mock_chunk_cls.create.call_args.kwargs
            assert call_kwargs["embedding"] == mock_embedding
            assert len(call_kwargs["embedding"]) == 768

    @pytest.mark.asyncio
    async def test_seed_medicine_extracts_keywords(self) -> None:
        """Test that seeding extracts keywords from contraindications."""
        medicine = {
            "id": 4,
            "name": "게보린정",
            "ingredient": "아세트아미노펜, 이소프로필안티피린",
            "disclaimer": "공복 복용 피할 것",
            "contraindicated_drugs": ["진정제", "다른 진통제"],
            "contraindicated_foods": ["술", "고카페인"],
            "usage": "강한 진통",
        }

        mock_embedding = [0.2] * 768

        with (
            patch("scripts.seed_rag_data.PharmaceuticalDocument") as mock_doc_cls,
            patch("scripts.seed_rag_data.DocumentChunk") as mock_chunk_cls,
            patch(
                "scripts.seed_rag_data.generate_embedding",
                new_callable=AsyncMock,
                return_value=mock_embedding,
            ),
        ):
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc_cls.create = AsyncMock(return_value=mock_doc)
            mock_chunk_cls.create = AsyncMock()
            # Mock filter().first() chain for existence check
            mock_filter = MagicMock()
            mock_filter.first = AsyncMock(return_value=None)
            mock_chunk_cls.filter = MagicMock(return_value=mock_filter)

            await seed_medicine_to_db(medicine)

            call_kwargs = mock_chunk_cls.create.call_args.kwargs
            keywords = call_kwargs["keywords"]
            assert "진정제" in keywords
            assert "술" in keywords


class TestEmbeddingGeneration:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_768_dimensions(self) -> None:
        """Test that embedding generation returns 768-dimensional vector."""
        import numpy as np

        from scripts.seed_rag_data import generate_embedding

        mock_embedding = np.array([0.1] * 768)

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=mock_embedding)
            mock_get_model.return_value = mock_model

            result = await generate_embedding("테스트 텍스트")

            assert len(result) == 768
            mock_model.encode.assert_called_once_with("테스트 텍스트")

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_normalized_vector(self) -> None:
        """Test that embedding is L2-normalized."""
        import numpy as np

        from scripts.seed_rag_data import generate_embedding

        # Non-normalized vector
        mock_embedding = np.array([3.0, 4.0] + [0.0] * 766)

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=mock_embedding)
            mock_get_model.return_value = mock_model

            result = await generate_embedding("테스트 텍스트")

            # Check L2 norm is approximately 1
            norm = np.linalg.norm(result)
            assert abs(norm - 1.0) < 0.001
