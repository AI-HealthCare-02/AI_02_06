"""RAG retrieval dispatch 계약 테스트 (옵션 C 2단계).

검증 대상:
- ``ai_worker.domains.rag.retrieval.retrieve_medicine_chunks`` —
  query 임베딩 + HybridRetriever 호출 + chunk 직렬화
- ``ai_worker.domains.tool_calling.jobs._dispatch`` —
  ``search_medicine_knowledge_base`` 분기로 retrieval 호출
- ``run_tool_calls_job`` — RAG 호출 포함 시 Tortoise lifecycle 관리

OpenAI / SentenceTransformer / 실제 Tortoise 는 monkeypatch 로 차단한다.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest


def _fake_search_result(name: str, section: str, content: str, score: float) -> Any:
    """``SearchResult`` 의 ducktype mock — retrieve() 결과 흉내."""
    chunk = MagicMock()
    chunk.section = section
    chunk.content = content
    chunk_match = MagicMock()
    chunk_match.chunk = chunk
    chunk_match.vector_score = score
    medicine = MagicMock()
    medicine.medicine_name = name
    result = MagicMock()
    result.medicine = medicine
    result.matched_chunks = [chunk_match]
    return result


# ── retrieval 모듈 ────────────────────────────────────────────────


class TestRetrieveMedicineChunks:
    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_chunks(self) -> None:
        from ai_worker.domains.rag import retrieval

        result = await retrieval.retrieve_medicine_chunks(query="")

        assert result["chunks"] == []
        assert result.get("note") == "empty query"

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty_chunks(self) -> None:
        from ai_worker.domains.rag import retrieval

        result = await retrieval.retrieve_medicine_chunks(query="   \n\t  ")

        assert result["chunks"] == []

    @pytest.mark.asyncio
    async def test_calls_encode_text_and_retriever(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.rag import retrieval

        captured: dict[str, Any] = {}

        async def fake_encode(text: str) -> list[float]:
            captured["embed_text"] = text
            return [0.1] * 768

        async def fake_retrieve(self, *, query: str, query_embedding, filters, limit) -> list:  # noqa: ARG001
            captured["retrieve_query"] = query
            captured["retrieve_limit"] = limit
            captured["embedding_dim"] = len(query_embedding)
            return [_fake_search_result("타이레놀", "side_effects", "위장 장애 가능", 0.87)]

        monkeypatch.setattr(retrieval, "encode_text", fake_encode)
        monkeypatch.setattr(retrieval.HybridRetriever, "retrieve", fake_retrieve)

        result = await retrieval.retrieve_medicine_chunks(query="타이레놀 부작용")

        assert captured["embed_text"] == "타이레놀 부작용"
        assert captured["retrieve_query"] == "타이레놀 부작용"
        assert captured["retrieve_limit"] == retrieval.DEFAULT_MAX_RESULTS
        assert captured["embedding_dim"] == 768

        assert len(result["chunks"]) == 1
        chunk = result["chunks"][0]
        assert chunk["medicine_name"] == "타이레놀"
        assert chunk["section"] == "side_effects"
        assert chunk["content"] == "위장 장애 가능"
        assert chunk["score"] == 0.87

    @pytest.mark.asyncio
    async def test_multiple_results_flatten_chunks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.rag import retrieval

        async def fake_encode(text: str) -> list[float]:  # noqa: ARG001
            return [0.0] * 768

        async def fake_retrieve(self, **_kwargs) -> list:  # noqa: ARG001
            return [
                _fake_search_result("아스피린", "efficacy", "통증 완화", 0.91),
                _fake_search_result("타이레놀", "efficacy", "해열", 0.83),
            ]

        monkeypatch.setattr(retrieval, "encode_text", fake_encode)
        monkeypatch.setattr(retrieval.HybridRetriever, "retrieve", fake_retrieve)

        result = await retrieval.retrieve_medicine_chunks(query="해열제")

        names = [c["medicine_name"] for c in result["chunks"]]
        assert names == ["아스피린", "타이레놀"]

    @pytest.mark.asyncio
    async def test_zero_results_returns_empty_chunks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.rag import retrieval

        async def fake_encode(text: str) -> list[float]:  # noqa: ARG001
            return [0.0] * 768

        async def fake_retrieve(self, **_kwargs) -> list:  # noqa: ARG001
            return []

        monkeypatch.setattr(retrieval, "encode_text", fake_encode)
        monkeypatch.setattr(retrieval.HybridRetriever, "retrieve", fake_retrieve)

        result = await retrieval.retrieve_medicine_chunks(query="없는약")

        assert result["chunks"] == []


# ── tool_calling/jobs.py dispatch ─────────────────────────────────


class TestDispatchMedicineKnowledge:
    @pytest.mark.asyncio
    async def test_medicine_call_routes_to_retrieval(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        captured: dict[str, Any] = {}

        async def fake_retrieve(query: str, max_results: int = 5) -> dict[str, Any]:
            captured["query"] = query
            captured["max_results"] = max_results
            return {"chunks": [{"medicine_name": "타이레놀", "section": "x", "content": "y", "score": 0.9}]}

        monkeypatch.setattr(tt, "retrieve_medicine_chunks", fake_retrieve)
        # Tortoise lifecycle 차단 — DB 없는 환경에서도 실행 가능해야 함
        monkeypatch.setattr(tt.Tortoise, "init", _noop_async_classmethod)
        monkeypatch.setattr(tt.Tortoise, "close_connections", _noop_async_classmethod)

        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_medicine_knowledge_base",
                    "arguments": {"query": "타이레놀 부작용"},
                },
            ],
        )

        assert captured["query"] == "타이레놀 부작용"
        assert "c1" in result
        assert result["c1"]["chunks"][0]["medicine_name"] == "타이레놀"

    @pytest.mark.asyncio
    async def test_tortoise_lifecycle_invoked_when_rag_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        lifecycle: list[str] = []

        async def fake_init(*, config) -> None:  # noqa: ARG001
            lifecycle.append("init")

        async def fake_close() -> None:
            lifecycle.append("close")

        async def fake_retrieve(query: str, max_results: int = 5) -> dict[str, Any]:  # noqa: ARG001
            lifecycle.append("retrieve")
            return {"chunks": []}

        monkeypatch.setattr(tt.Tortoise, "init", fake_init)
        monkeypatch.setattr(tt.Tortoise, "close_connections", fake_close)
        monkeypatch.setattr(tt, "retrieve_medicine_chunks", fake_retrieve)

        await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_medicine_knowledge_base",
                    "arguments": {"query": "x"},
                },
            ],
        )

        # init 가 dispatch 보다 먼저, close 가 마지막에 호출되어야 함
        assert lifecycle == ["init", "retrieve", "close"]

    @pytest.mark.asyncio
    async def test_tortoise_lifecycle_skipped_when_no_rag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        lifecycle: list[str] = []

        async def fake_init(*, config) -> None:  # noqa: ARG001
            lifecycle.append("init")

        async def fake_close() -> None:
            lifecycle.append("close")

        async def fake_kw(*, query: str):  # noqa: ARG001
            return []

        monkeypatch.setattr(tt.Tortoise, "init", fake_init)
        monkeypatch.setattr(tt.Tortoise, "close_connections", fake_close)
        monkeypatch.setattr(tt, "search_hospitals_by_keyword", fake_kw)

        await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_keyword",
                    "arguments": {"query": "강남역 약국"},
                },
            ],
        )

        # 위치 검색만 도는 turn 은 Tortoise 를 절대 열지 않아야 함
        assert lifecycle == []

    @pytest.mark.asyncio
    async def test_tortoise_closed_even_on_dispatch_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        lifecycle: list[str] = []

        async def fake_init(*, config) -> None:  # noqa: ARG001
            lifecycle.append("init")

        async def fake_close() -> None:
            lifecycle.append("close")

        async def boom(query: str, max_results: int = 5) -> dict[str, Any]:  # noqa: ARG001
            raise RuntimeError("retrieval boom")

        monkeypatch.setattr(tt.Tortoise, "init", fake_init)
        monkeypatch.setattr(tt.Tortoise, "close_connections", fake_close)
        monkeypatch.setattr(tt, "retrieve_medicine_chunks", boom)

        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_medicine_knowledge_base",
                    "arguments": {"query": "x"},
                },
            ],
        )

        assert lifecycle == ["init", "close"]  # close 항상 호출
        assert "error" in result["c1"]
        assert "retrieval boom" in result["c1"]["error"]


async def _noop_async_classmethod(*_args, **_kwargs) -> None:
    """Tortoise.init / close_connections 을 차단하기 위한 noop async."""
    return
