"""Tests for the batched RAG seeding path.

The batched API encodes every chunk text in a single SentenceTransformer
call and persists rows via bulk_create, so large seed sets (tens of
thousands) complete in minutes rather than hours. Covers text building,
batch encoding, existing-row filtering, and the bulk_create invocation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from scripts.seed_rag_data import (
    build_chunk_texts,
    filter_new_medicines,
    generate_embeddings_batch,
    seed_batch,
)


def _medicine(idx: int, name: str) -> dict:
    """Factory for a minimal medicines.json-shaped dict."""
    return {
        "id": idx,
        "name": name,
        "ingredient": f"성분{idx}",
        "usage": "해열진통",
        "disclaimer": "주의",
        "contraindicated_drugs": [],
        "contraindicated_foods": [],
    }


class TestBuildChunkTexts:
    """Tests for batch text construction."""

    def test_returns_one_text_per_medicine(self) -> None:
        medicines = [_medicine(1, "약A"), _medicine(2, "약B"), _medicine(3, "약C")]

        texts = build_chunk_texts(medicines)

        assert len(texts) == 3
        assert "[약A]" in texts[0]
        assert "[약B]" in texts[1]
        assert "[약C]" in texts[2]

    def test_preserves_input_order(self) -> None:
        medicines = [_medicine(1, f"약{i}") for i in range(5)]

        texts = build_chunk_texts(medicines)

        for i, text in enumerate(texts):
            assert f"[약{i}]" in text


class TestGenerateEmbeddingsBatch:
    """Tests for batched embedding generation."""

    @pytest.mark.asyncio
    async def test_calls_model_encode_once_with_full_batch(self) -> None:
        texts = [f"text-{i}" for i in range(5)]
        mock_matrix = np.ones((5, 768), dtype=np.float32)

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get:
            model = MagicMock()
            model.encode = MagicMock(return_value=mock_matrix)
            mock_get.return_value = model

            await generate_embeddings_batch(texts)

            model.encode.assert_called_once()
            args, kwargs = model.encode.call_args
            assert list(args[0]) == texts or kwargs.get("sentences") == texts

    @pytest.mark.asyncio
    async def test_returns_one_normalized_vector_per_text(self) -> None:
        texts = ["a", "b"]
        mock_matrix = np.array([[3.0, 4.0] + [0.0] * 766, [1.0, 0.0] + [0.0] * 766])

        with patch("scripts.seed_rag_data.get_embedding_model") as mock_get:
            model = MagicMock()
            model.encode = MagicMock(return_value=mock_matrix)
            mock_get.return_value = model

            vectors = await generate_embeddings_batch(texts)

            assert len(vectors) == 2
            assert len(vectors[0]) == 768
            assert abs(np.linalg.norm(vectors[0]) - 1.0) < 0.001
            assert abs(np.linalg.norm(vectors[1]) - 1.0) < 0.001


class TestFilterNewMedicines:
    """Tests for idempotent filtering of already-seeded rows."""

    @pytest.mark.asyncio
    async def test_drops_existing_names(self) -> None:
        medicines = [_medicine(1, "약A"), _medicine(2, "약B"), _medicine(3, "약C")]

        with patch("scripts.seed_rag_data.MedicineInfo") as mock_model:
            existing_queryset = MagicMock()
            existing_queryset.values_list = AsyncMock(return_value=["약A", "약C"])
            mock_model.filter = MagicMock(return_value=existing_queryset)

            result = await filter_new_medicines(medicines)

            assert [m["name"] for m in result] == ["약B"]

    @pytest.mark.asyncio
    async def test_returns_all_when_nothing_exists(self) -> None:
        medicines = [_medicine(1, "약A"), _medicine(2, "약B")]

        with patch("scripts.seed_rag_data.MedicineInfo") as mock_model:
            existing_queryset = MagicMock()
            existing_queryset.values_list = AsyncMock(return_value=[])
            mock_model.filter = MagicMock(return_value=existing_queryset)

            result = await filter_new_medicines(medicines)

            assert [m["name"] for m in result] == ["약A", "약B"]


class TestSeedBatch:
    """Tests for the batch-level seeding entry point."""

    @pytest.mark.asyncio
    async def test_uses_bulk_create_not_individual_create(self) -> None:
        medicines = [_medicine(1, "약A"), _medicine(2, "약B")]
        mock_embeddings = [[0.1] * 768, [0.2] * 768]

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=mock_embeddings,
            ),
        ):
            mock_model.bulk_create = AsyncMock()

            await seed_batch(medicines)

            mock_model.bulk_create.assert_called_once()
            objects = mock_model.bulk_create.call_args.args[0]
            assert len(objects) == 2

    @pytest.mark.asyncio
    async def test_dry_run_skips_bulk_create(self) -> None:
        medicines = [_medicine(1, "약A")]

        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=[[0.3] * 768],
            ) as mock_embed,
        ):
            mock_model.bulk_create = AsyncMock()

            await seed_batch(medicines, dry_run=True)

            mock_model.bulk_create.assert_not_called()
            mock_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_input_is_noop(self) -> None:
        with (
            patch("scripts.seed_rag_data.MedicineInfo") as mock_model,
            patch(
                "scripts.seed_rag_data.generate_embeddings_batch",
                new_callable=AsyncMock,
            ) as mock_embed,
        ):
            mock_model.bulk_create = AsyncMock()

            await seed_batch([])

            mock_model.bulk_create.assert_not_called()
            mock_embed.assert_not_called()
