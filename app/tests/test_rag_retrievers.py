"""Tests for Retriever implementations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dtos.rag import SearchFilters, SearchResult
from app.services.rag.retrievers.hybrid import HybridRetriever


class TestHybridRetriever:
    """Test HybridRetriever implementation."""

    def test_retriever_has_default_weights(self) -> None:
        """HybridRetriever must have default vector/keyword weights."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)
        assert hasattr(retriever, "vector_weight")
        assert hasattr(retriever, "keyword_weight")

    def test_weights_sum_to_one(self) -> None:
        """vector_weight + keyword_weight must equal 1.0."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)
        total = retriever.vector_weight + retriever.keyword_weight
        assert abs(total - 1.0) < 1e-6

    def test_retriever_accepts_custom_weights(self) -> None:
        """HybridRetriever must accept custom weights."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(
            embedding_provider=mock_provider,
            vector_weight=0.8,
            keyword_weight=0.2,
        )
        assert retriever.vector_weight == pytest.approx(0.8)
        assert retriever.keyword_weight == pytest.approx(0.2)

    @pytest.mark.asyncio
    async def test_retrieve_returns_list(self) -> None:
        """Retrieve must return a list (DB mocked)."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)
        retriever._vector_search = AsyncMock(return_value=[])  # noqa: SLF001

        result = await retriever.retrieve(
            query="타이레놀 부작용",
            query_embedding=[0.1] * 768,
            filters=SearchFilters(),
            limit=5,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_retrieve_results_are_search_result_instances(self) -> None:
        """Retrieve results must be SearchResult instances (DB mocked)."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)
        retriever._vector_search = AsyncMock(return_value=[])  # noqa: SLF001

        result = await retriever.retrieve(
            query="test",
            query_embedding=[0.1] * 768,
            filters=SearchFilters(),
            limit=5,
        )
        for item in result:
            assert isinstance(item, SearchResult)

    @pytest.mark.asyncio
    async def test_retrieve_respects_limit(self) -> None:
        """Retrieve must not return more results than limit (DB mocked)."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)
        retriever._vector_search = AsyncMock(return_value=[])  # noqa: SLF001

        result = await retriever.retrieve(
            query="test",
            query_embedding=[0.1] * 768,
            filters=SearchFilters(),
            limit=3,
        )
        assert len(result) <= 3

    def test_keyword_score_calculation(self) -> None:
        """Keyword score must be between 0 and 1."""
        mock_provider = MagicMock()
        retriever = HybridRetriever(embedding_provider=mock_provider)

        score = retriever.calculate_keyword_score(
            query_keywords=["타이레놀", "부작용"],
            chunk_keywords=["타이레놀"],
            chunk_content="타이레놀은 해열진통제입니다.",
        )
        assert 0.0 <= score <= 1.0
