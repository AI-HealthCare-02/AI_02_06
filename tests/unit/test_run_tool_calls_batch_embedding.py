"""Unit tests for ai_worker.domains.tool_calling.jobs batch embedding 최적화.

PLAN.md (fix/rag-batch-embedding) - fan-out N 개 RAG 호출의 임베딩을
1회 OpenAI API call 로 묶는 최적화. 본 테스트는 다음을 검증한다:

- search_medicine_knowledge_base x N -> encode_queries_batch 1회 호출
- 사전계산된 embedding 이 retrieve_medicine_chunks 의
  ``precomputed_embedding`` 인자로 정확히 매핑됨
- RAG 호출이 없으면 batch 임베딩 skip
- retrieve_medicine_chunks 자체의 precomputed_embedding 분기
"""

from __future__ import annotations

from typing import Any

import pytest

from ai_worker.domains.rag import retrieval as rag_retrieval
from ai_worker.domains.tool_calling import jobs as tool_jobs


class _SpyEmbedder:
    """encode_queries_batch / encode_query 호출을 기록하는 spy."""

    def __init__(self, dim: int = 3072) -> None:
        self.batch_calls: list[list[str]] = []
        self.single_calls: list[str] = []
        self._dim = dim

    async def batch(self, queries: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(queries))
        return [[float(i)] * self._dim for i, _ in enumerate(queries)]

    async def single(self, query: str) -> list[float]:
        self.single_calls.append(query)
        return [9.9] * self._dim


@pytest.fixture
def spy_embedder(monkeypatch: pytest.MonkeyPatch) -> _SpyEmbedder:
    spy = _SpyEmbedder()
    monkeypatch.setattr(tool_jobs, "encode_queries_batch", spy.batch)
    monkeypatch.setattr(rag_retrieval, "encode_query", spy.single)
    return spy


@pytest.fixture
def stub_retrieval(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """retrieve_medicine_chunks 호출 인자를 기록해 검증할 수 있게 한다."""
    captured: list[dict[str, Any]] = []

    async def fake_retrieve(
        query: str,
        max_results: int = 5,
        *,
        precomputed_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        captured.append({
            "query": query,
            "max_results": max_results,
            "precomputed_embedding": precomputed_embedding,
        })
        return {"chunks": []}

    monkeypatch.setattr(tool_jobs, "retrieve_medicine_chunks", fake_retrieve)
    return captured


@pytest.fixture
def no_tortoise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tortoise.init / close_connections 를 no-op 으로 대체."""

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(tool_jobs.Tortoise, "init", _noop)
    monkeypatch.setattr(tool_jobs.Tortoise, "close_connections", _noop)


class TestRunToolCallsBatchEmbedding:
    """run_tool_calls_job 의 batch 임베딩 동작 검증."""

    @pytest.mark.asyncio
    async def test_seven_rag_calls_trigger_one_batch_embedding(
        self,
        spy_embedder: _SpyEmbedder,
        stub_retrieval: list[dict[str, Any]],  # noqa: ARG002 — fixture setup 효과
        no_tortoise: None,  # noqa: ARG002 — fixture setup 효과
    ) -> None:
        """7개 RAG fan-out -> encode_queries_batch 1회 호출, 단건 호출 0회."""
        queries = [f"q{i}" for i in range(7)]
        calls = [
            {
                "tool_call_id": f"call_{i}",
                "name": "search_medicine_knowledge_base",
                "arguments": {"query": queries[i]},
            }
            for i in range(7)
        ]

        result = await tool_jobs.run_tool_calls_job(calls)

        assert len(result) == 7
        assert len(spy_embedder.batch_calls) == 1
        assert spy_embedder.batch_calls[0] == queries
        assert spy_embedder.single_calls == []

    @pytest.mark.asyncio
    async def test_precomputed_embedding_threaded_into_retrieve(
        self,
        spy_embedder: _SpyEmbedder,  # noqa: ARG002 — fixture setup 효과
        stub_retrieval: list[dict[str, Any]],
        no_tortoise: None,  # noqa: ARG002 — fixture setup 효과
    ) -> None:
        """batch 임베딩 결과가 각 retrieve_medicine_chunks 호출에 정확히 매핑."""
        calls = [
            {
                "tool_call_id": "call_a",
                "name": "search_medicine_knowledge_base",
                "arguments": {"query": "타이레놀"},
            },
            {
                "tool_call_id": "call_b",
                "name": "search_medicine_knowledge_base",
                "arguments": {"query": "메트포민"},
            },
        ]

        await tool_jobs.run_tool_calls_job(calls)

        assert len(stub_retrieval) == 2
        first = next(c for c in stub_retrieval if c["query"] == "타이레놀")
        second = next(c for c in stub_retrieval if c["query"] == "메트포민")
        assert first["precomputed_embedding"] is not None
        assert second["precomputed_embedding"] is not None
        assert first["precomputed_embedding"][0] == 0.0
        assert second["precomputed_embedding"][0] == 1.0

    @pytest.mark.asyncio
    async def test_no_rag_calls_skips_batch_embedding(
        self,
        spy_embedder: _SpyEmbedder,
        stub_retrieval: list[dict[str, Any]],  # noqa: ARG002 — fixture setup 효과
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RAG 호출이 없으면 batch 임베딩 skip + Tortoise lifecycle skip."""

        async def fake_keyword(_call: dict[str, Any]) -> dict[str, Any]:
            return {"places": []}

        monkeypatch.setattr(tool_jobs, "_run_keyword", fake_keyword)
        calls = [
            {
                "tool_call_id": "call_x",
                "name": "search_hospitals_by_keyword",
                "arguments": {"query": "서울 약국"},
            }
        ]
        result = await tool_jobs.run_tool_calls_job(calls)

        assert len(result) == 1
        assert spy_embedder.batch_calls == []
        assert spy_embedder.single_calls == []


class TestRetrieveMedicineChunksPrecomputed:
    """retrieve_medicine_chunks 의 precomputed_embedding 분기 검증."""

    @pytest.mark.asyncio
    async def test_precomputed_embedding_skips_encode_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """precomputed_embedding 전달 시 encode_query 호출되지 않음."""
        encode_calls: list[str] = []

        async def fake_encode(query: str) -> list[float]:
            encode_calls.append(query)
            return [0.0] * 3072

        retriever_calls: list[dict[str, Any]] = []

        class _FakeRetriever:
            def __init__(self, *_a: Any, **_k: Any) -> None:
                pass

            async def retrieve(self, **kwargs: Any) -> list[Any]:
                retriever_calls.append(kwargs)
                return []

        monkeypatch.setattr(rag_retrieval, "encode_query", fake_encode)
        monkeypatch.setattr(rag_retrieval, "HybridRetriever", _FakeRetriever)

        precomputed = [0.5] * 3072
        out = await rag_retrieval.retrieve_medicine_chunks(
            query="타이레놀 부작용",
            precomputed_embedding=precomputed,
        )

        assert out == {"chunks": []}
        assert encode_calls == []
        assert retriever_calls[0]["query_embedding"] is precomputed

    @pytest.mark.asyncio
    async def test_no_precomputed_falls_back_to_encode_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """precomputed_embedding 미전달 시 기존대로 encode_query 호출 (하위호환)."""
        encode_calls: list[str] = []

        async def fake_encode(query: str) -> list[float]:
            encode_calls.append(query)
            return [0.7] * 3072

        retriever_calls: list[dict[str, Any]] = []

        class _FakeRetriever:
            def __init__(self, *_a: Any, **_k: Any) -> None:
                pass

            async def retrieve(self, **kwargs: Any) -> list[Any]:
                retriever_calls.append(kwargs)
                return []

        monkeypatch.setattr(rag_retrieval, "encode_query", fake_encode)
        monkeypatch.setattr(rag_retrieval, "HybridRetriever", _FakeRetriever)

        await rag_retrieval.retrieve_medicine_chunks(query="아세트아미노펜")

        assert encode_calls == ["아세트아미노펜"]
        assert retriever_calls[0]["query_embedding"] == [0.7] * 3072
