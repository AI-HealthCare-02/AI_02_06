"""Unit tests for app.services.rag.openai_embedding — 사용자 query 측 임베딩.

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 AsyncOpenAI mock 으로 실 호출 검증.

PLAN.md §4.1 — text-embedding-3-large + dimensions=3072 검증:
- encode_query → 단일 query → 3072 float list
- encode_queries_batch → N query → list of N vectors (단일 API 호출)
- 빈 문자열 → 영벡터 (3072 zeros)
"""

from __future__ import annotations

import pytest

from app.services.rag.openai_embedding import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    encode_queries_batch,
    encode_query,
)


class TestConstants:
    """모델/차원 상수가 chunk 임베딩과 일치하는지."""

    def test_model_name(self) -> None:
        assert EMBEDDING_MODEL == "text-embedding-3-large"

    def test_dimensions(self) -> None:
        assert EMBEDDING_DIMENSIONS == 3072


class TestEncodeQuery:
    """encode_query 단위 테스트 (Red 상태)."""

    @pytest.mark.asyncio
    async def test_single_query_returns_3072_vector(self) -> None:
        """정상 query → 3072 차원 float list."""
        with pytest.raises(NotImplementedError):
            await encode_query("타이레놀 부작용")

    @pytest.mark.asyncio
    async def test_empty_string(self) -> None:
        """빈 문자열도 호출 가능 (영벡터 또는 OpenAI BadRequestError fallback)."""
        with pytest.raises(NotImplementedError):
            await encode_query("")


class TestEncodeQueriesBatch:
    """encode_queries_batch 단위 테스트 (Red 상태)."""

    @pytest.mark.asyncio
    async def test_batch_returns_n_vectors(self) -> None:
        """N query → N vectors (단일 OpenAI API call)."""
        queries = [
            "타이레놀과 와파린 상호작용",
            "메트포민의 부작용",
            "오메가3 복용 주의사항",
        ]
        with pytest.raises(NotImplementedError):
            await encode_queries_batch(queries)

    @pytest.mark.asyncio
    async def test_empty_batch(self) -> None:
        """빈 list → 빈 list (API 호출 X)."""
        with pytest.raises(NotImplementedError):
            await encode_queries_batch([])
