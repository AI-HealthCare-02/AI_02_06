"""Tests for EmbeddingProvider implementations."""

from unittest.mock import MagicMock

import pytest

from app.services.rag.providers.sentence_transformer import SentenceTransformerProvider


class TestSentenceTransformerProvider:
    """Test SentenceTransformerProvider implementation."""

    def test_provider_has_default_model_name(self) -> None:
        """Provider must have a default Korean model name."""
        provider = SentenceTransformerProvider()
        assert provider.model_name is not None
        assert isinstance(provider.model_name, str)

    def test_provider_dimensions_property(self) -> None:
        """Provider must expose dimensions property."""
        provider = SentenceTransformerProvider()
        assert isinstance(provider.dimensions, int)
        assert provider.dimensions > 0

    def test_provider_accepts_custom_model_name(self) -> None:
        """Provider must accept custom model name."""
        provider = SentenceTransformerProvider(model_name="custom/model")
        assert provider.model_name == "custom/model"

    @pytest.mark.asyncio
    async def test_encode_single_raises_before_initialize(self) -> None:
        """encode_single must raise RuntimeError if not initialized."""
        provider = SentenceTransformerProvider()
        with pytest.raises(RuntimeError):
            await provider.encode_single("test")

    @pytest.mark.asyncio
    async def test_encode_single_returns_normalized_vector(self) -> None:
        """encode_single must return a normalized float list."""
        import numpy as np

        provider = SentenceTransformerProvider()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([3.0, 4.0, 0.0])
        mock_model.get_sentence_embedding_dimension.return_value = 3
        provider.model = mock_model
        provider.dimensions = 3

        result = await provider.encode_single("test text")

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)
        norm = sum(v**2 for v in result) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_encode_batch_returns_correct_count(self) -> None:
        """encode_batch must return same number of vectors as input texts."""
        import numpy as np

        provider = SentenceTransformerProvider()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        mock_model.get_sentence_embedding_dimension.return_value = 2
        provider.model = mock_model
        provider.dimensions = 2

        result = await provider.encode_batch(["text1", "text2", "text3"])

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_encode_single_empty_text_returns_zero_vector(self) -> None:
        """encode_single with empty text must return zero vector."""
        provider = SentenceTransformerProvider()
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        provider.model = mock_model
        provider.dimensions = 768

        result = await provider.encode_single("")

        assert isinstance(result, list)
        assert len(result) == 768
        assert all(v == 0.0 for v in result)
