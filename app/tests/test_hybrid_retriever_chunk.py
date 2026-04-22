"""Tests for HybridRetriever operating over medicine_chunk + medicine_info.

The retriever now runs its pgvector search against `medicine_chunk.embedding`
and surfaces results as `SearchResult(medicine, matched_chunks[], scores)`.
Multiple chunks from the same medicine are grouped under one SearchResult.

These tests exercise the pure logic parts that don't need a live DB:
  - keyword scoring against medicine_name + category
  - chunk grouping by parent medicine_info
  - retrieve() contract: returns list[SearchResult] sorted by final_score
"""

from unittest.mock import MagicMock

from app.dtos.rag import ChunkMatch, SearchFilters, SearchResult
from app.models.medicine_chunk import MedicineChunk
from app.models.medicine_info import MedicineInfo
from app.services.rag.retrievers.hybrid import HybridRetriever


def _make_medicine(medicine_id: int, name: str, category: str | None = None) -> MedicineInfo:
    """Build a minimally-shaped MedicineInfo stub."""
    return MedicineInfo(
        id=medicine_id,
        item_seq=f"ITEM{medicine_id:04d}",
        medicine_name=name,
        category=category,
    )


def _make_chunk(medicine_id: int, section: str, content: str, chunk_index: int = 0) -> MedicineChunk:
    """Build a minimally-shaped MedicineChunk stub."""
    return MedicineChunk(
        id=medicine_id * 100 + chunk_index,
        medicine_info_id=medicine_id,
        section=section,
        chunk_index=chunk_index,
        content=content,
        token_count=len(content),
        embedding=None,
        model_version="ko-sroberta-multitask-v1",
    )


def _make_retriever() -> HybridRetriever:
    provider = MagicMock()
    provider.dimensions = 768
    return HybridRetriever(embedding_provider=provider)


class TestKeywordScore:
    """Keyword score runs against medicine_name + category, not legacy fields."""

    def test_zero_when_no_query_keywords(self) -> None:
        retriever = _make_retriever()
        score = retriever.calculate_keyword_score(
            query_keywords=[],
            medicine_name="타이레놀정 500mg",
            category="해열진통제",
        )
        assert score == 0.0

    def test_name_hit_scores_higher_than_category_hit(self) -> None:
        retriever = _make_retriever()
        name_hit = retriever.calculate_keyword_score(
            query_keywords=["타이레놀"],
            medicine_name="타이레놀정 500mg",
            category="해열진통제",
        )
        category_hit = retriever.calculate_keyword_score(
            query_keywords=["해열"],
            medicine_name="아스피린",
            category="해열진통제",
        )
        assert name_hit > category_hit

    def test_score_bounded_in_unit_interval(self) -> None:
        retriever = _make_retriever()
        score = retriever.calculate_keyword_score(
            query_keywords=["타이레놀", "복용", "부작용"],
            medicine_name="타이레놀정 500mg",
            category="해열진통제",
        )
        assert 0.0 <= score <= 1.0

    def test_accepts_null_category(self) -> None:
        """category is nullable on the main schema; scorer must not crash."""
        retriever = _make_retriever()
        score = retriever.calculate_keyword_score(
            query_keywords=["타이레놀"],
            medicine_name="타이레놀정 500mg",
            category=None,
        )
        assert 0.0 <= score <= 1.0


class TestGroupChunksByMedicine:
    """Multiple chunks from the same parent medicine must collapse into one entry."""

    def test_groups_by_medicine_id(self) -> None:
        retriever = _make_retriever()
        tylenol = _make_medicine(1, "타이레놀정 500mg", "해열진통제")
        gebolin = _make_medicine(2, "게보린정", "해열진통제")

        raw_hits: list[tuple[MedicineInfo, MedicineChunk, float]] = [
            (tylenol, _make_chunk(1, "efficacy", "해열 효과"), 0.82),
            (tylenol, _make_chunk(1, "usage", "1회 1정", chunk_index=1), 0.65),
            (gebolin, _make_chunk(2, "efficacy", "강한 진통"), 0.74),
        ]

        grouped = retriever._group_chunks_by_medicine(raw_hits)
        assert len(grouped) == 2
        assert grouped[0][0].id == 1  # preserved input order by best score
        assert len(grouped[0][1]) == 2  # two chunks under tylenol
        assert grouped[1][0].id == 2

    def test_representative_vector_score_is_top1(self) -> None:
        retriever = _make_retriever()
        med = _make_medicine(1, "타이레놀정 500mg", "해열진통제")
        raw_hits = [
            (med, _make_chunk(1, "efficacy", "..."), 0.82),
            (med, _make_chunk(1, "usage", "...", chunk_index=1), 0.65),
        ]
        grouped = retriever._group_chunks_by_medicine(raw_hits)
        _medicine, chunk_matches = grouped[0]
        # top-1 stays first, all chunks preserved
        assert chunk_matches[0].vector_score == 0.82
        assert chunk_matches[-1].vector_score == 0.65


class TestRetrieveContract:
    """retrieve() returns aggregated SearchResult with matched_chunks populated."""

    async def test_empty_vector_search_returns_empty(self) -> None:
        retriever = _make_retriever()

        async def _empty(*_args: object, **_kwargs: object) -> list:
            return []

        retriever._vector_search = _empty  # type: ignore[method-assign]

        results = await retriever.retrieve(
            query="아무거나",
            query_embedding=[0.0] * 768,
            filters=SearchFilters(),
            limit=5,
        )
        assert results == []

    async def test_search_result_carries_matched_chunks(self) -> None:
        retriever = _make_retriever()
        med = _make_medicine(1, "타이레놀정 500mg", "해열진통제")
        chunks = [
            ChunkMatch(chunk=_make_chunk(1, "efficacy", "해열"), vector_score=0.82),
            ChunkMatch(chunk=_make_chunk(1, "usage", "복용", chunk_index=1), vector_score=0.65),
        ]

        async def _one(*_args: object, **_kwargs: object) -> list[tuple[MedicineInfo, list[ChunkMatch]]]:
            return [(med, chunks)]

        retriever._vector_search = _one  # type: ignore[method-assign]

        results = await retriever.retrieve(
            query="타이레놀",
            query_embedding=[0.0] * 768,
            filters=SearchFilters(),
            limit=5,
        )
        assert len(results) == 1
        r: SearchResult = results[0]
        assert r.medicine.medicine_name == "타이레놀정 500mg"
        assert len(r.matched_chunks) == 2
        assert r.vector_score == 0.82  # representative = top-1 chunk
