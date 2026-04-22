"""Tests for the MedicineInfo-backed HybridRetriever.

Validates the pure-Python scoring logic (keyword extraction, keyword score)
and the shape of the retrieve() contract after the DocumentChunk -> MedicineInfo
redesign. DB interaction is covered by integration tests run against a
live pgvector DB; here we only exercise deterministic helpers.
"""

# ruff: noqa: SLF001
from typing import Any
from unittest.mock import MagicMock

from app.dtos.rag import SearchFilters, SearchResult
from app.models.medicine_info import MedicineInfo
from app.services.rag.retrievers.hybrid import HybridRetriever


def _make_retriever() -> HybridRetriever:
    """Construct a retriever with a no-op embedding provider stub."""
    provider = MagicMock()
    provider.dimensions = 768
    return HybridRetriever(embedding_provider=provider)


class TestKeywordExtraction:
    """Tests for Korean keyword extraction."""

    def test_extracts_content_words(self) -> None:
        retriever = _make_retriever()

        keywords = retriever.extract_keywords("타이레놀의 부작용이 뭐야")

        assert "타이레놀" in keywords
        assert "부작용" in keywords

    def test_drops_stopwords_and_single_chars(self) -> None:
        retriever = _make_retriever()

        keywords = retriever.extract_keywords("이 약은 뭐야")

        assert "이" not in keywords
        assert "는" not in keywords


class TestKeywordScore:
    """Tests for keyword score computation against MedicineInfo-style rows."""

    def test_score_zero_when_no_query_keywords(self) -> None:
        retriever = _make_retriever()

        score = retriever.calculate_keyword_score(
            query_keywords=[],
            medicine_text="타이레놀은 해열진통제입니다",
            medicine_name="타이레놀",
        )

        assert score == 0.0

    def test_exact_name_match_scores_higher_than_content_match(self) -> None:
        retriever = _make_retriever()

        name_hit = retriever.calculate_keyword_score(
            query_keywords=["타이레놀"],
            medicine_text="해열진통제",
            medicine_name="타이레놀",
        )
        content_hit = retriever.calculate_keyword_score(
            query_keywords=["해열진통"],
            medicine_text="해열진통",
            medicine_name="게보린",
        )

        assert name_hit > content_hit

    def test_score_bounded_in_unit_interval(self) -> None:
        retriever = _make_retriever()

        score = retriever.calculate_keyword_score(
            query_keywords=["타이레놀", "부작용", "복용"],
            medicine_text="타이레놀 부작용 복용 타이레놀 부작용 복용",
            medicine_name="타이레놀",
        )

        assert 0.0 <= score <= 1.0


class TestRetrieveContract:
    """Tests for retrieve() return shape — empty candidates short-circuit."""

    async def test_retrieve_returns_empty_when_no_vector_hits(self) -> None:
        retriever = _make_retriever()

        async def _empty(*_args: Any, **_kwargs: Any) -> list[tuple[MedicineInfo, float]]:
            return []

        retriever._vector_search = _empty  # ty: ignore[method-assign]

        results = await retriever.retrieve(
            query="아무거나",
            query_embedding=[0.0] * 768,
            filters=SearchFilters(),
            limit=5,
        )

        assert results == []

    async def test_search_result_wraps_medicine_info(self) -> None:
        """SearchResult must expose a `medicine` field of type MedicineInfo."""
        retriever = _make_retriever()

        medicine = MagicMock(spec=MedicineInfo)
        medicine.name = "타이레놀"
        medicine.ingredient = "아세트아미노펜"
        medicine.usage = "해열진통"
        medicine.disclaimer = ""
        medicine.contraindicated_drugs = []
        medicine.contraindicated_foods = []

        async def _one(*_args: Any, **_kwargs: Any) -> list[tuple[MedicineInfo, float]]:
            return [(medicine, 0.9)]

        retriever._vector_search = _one  # ty: ignore[method-assign]

        results = await retriever.retrieve(
            query="타이레놀",
            query_embedding=[0.0] * 768,
            filters=SearchFilters(),
            limit=5,
        )

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].medicine is medicine
