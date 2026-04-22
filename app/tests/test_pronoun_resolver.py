"""Tests for multi-turn pronoun resolution helpers.

These helpers reuse the existing pgvector search output + stored message
metadata to resolve references like "그 약", "두 약", or subject-dropped
Korean queries without spending additional LLM calls.
"""

from app.dtos.rag import SearchResult
from app.models.medicine_info import MedicineInfo
from app.services.rag.pronoun_resolver import (
    collect_recent_medicine_names,
    has_medicine_reference,
)


def _make_search_result(name: str, score: float) -> SearchResult:
    """Build a SearchResult with a minimally-shaped MedicineInfo stub."""
    medicine = MedicineInfo(
        id=1,
        name=name,
        ingredient="성분",
        usage="해열진통",
        disclaimer="",
        contraindicated_drugs=[],
        contraindicated_foods=[],
        embedding=[0.0] * 768,
        embedding_normalized=True,
    )
    return SearchResult(
        medicine=medicine,
        vector_score=score,
        keyword_score=0.0,
        final_score=score,
    )


class TestHasMedicineReference:
    """Decide whether the current query already points to a concrete medicine."""

    def test_returns_true_when_top_similarity_meets_threshold(self) -> None:
        results = [_make_search_result("타이레놀정 500mg", 0.62)]
        assert has_medicine_reference(results, threshold=0.5) is True

    def test_returns_false_when_top_similarity_below_threshold(self) -> None:
        results = [_make_search_result("판콜에스", 0.32)]
        assert has_medicine_reference(results, threshold=0.5) is False

    def test_returns_false_on_empty_results(self) -> None:
        assert has_medicine_reference([], threshold=0.5) is False

    def test_default_threshold_is_reasonable(self) -> None:
        """Default threshold must exist and be a float in (0, 1)."""
        import inspect

        threshold_default = inspect.signature(has_medicine_reference).parameters["threshold"].default
        assert isinstance(threshold_default, float)
        assert 0.0 < threshold_default < 1.0


class TestCollectRecentMedicineNames:
    """Walk history metadata to collect recently mentioned medicines."""

    def test_returns_empty_for_empty_history(self) -> None:
        assert collect_recent_medicine_names([]) == []

    def test_collects_from_newest_first(self) -> None:
        # history ordered oldest → newest (same convention as pipeline input)
        history_metadata = [
            {"retrieval": {"medicine_names": ["타이레놀정 500mg"]}},
            {"retrieval": {"medicine_names": ["게보린정"]}},
            {"retrieval": {"medicine_names": ["까스활명수큐"]}},
        ]
        names = collect_recent_medicine_names(history_metadata)
        assert names[0] == "까스활명수큐"
        assert "게보린정" in names
        assert "타이레놀정 500mg" in names

    def test_deduplicates_preserving_recency(self) -> None:
        history_metadata = [
            {"retrieval": {"medicine_names": ["타이레놀정 500mg"]}},
            {"retrieval": {"medicine_names": ["타이레놀정 500mg", "판콜에스"]}},
        ]
        names = collect_recent_medicine_names(history_metadata)
        # newest turn came first in dedup order
        assert names[0] == "타이레놀정 500mg"
        assert "판콜에스" in names
        assert names.count("타이레놀정 500mg") == 1

    def test_respects_limit(self) -> None:
        history_metadata = [{"retrieval": {"medicine_names": [f"약{i}"]}} for i in range(10)]
        assert len(collect_recent_medicine_names(history_metadata, limit=3)) == 3

    def test_skips_entries_without_retrieval_key(self) -> None:
        history_metadata = [
            {"intent": "general_chat"},
            {"retrieval": {"medicine_names": ["타이레놀정 500mg"]}},
            {},
        ]
        names = collect_recent_medicine_names(history_metadata)
        assert names == ["타이레놀정 500mg"]

    def test_ignores_non_string_names(self) -> None:
        history_metadata = [
            {"retrieval": {"medicine_names": [None, 123, "게보린정"]}},
        ]
        assert collect_recent_medicine_names(history_metadata) == ["게보린정"]
