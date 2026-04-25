"""Tests for RAGGenerator.rewrite_query LLM-based query rewriting.

The rewriter turns multi-turn, pronoun-laden Korean queries into
self-contained single-turn queries. It returns a structured
RewriteResult so the pipeline can branch into three paths:

  ok           -> use rewritten query for retrieval
  unresolvable -> skip retrieval and ask the user to clarify
  fallback     -> use the original query (technical failure)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_worker.utils.rag import RAGGenerator
from app.dtos.rag import RewriteResult, RewriteStatus, TokenUsage


def _mock_openai_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 20) -> MagicMock:
    """Build a MagicMock shaped like openai.ChatCompletion."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


class TestRewriteStatusEnum:
    """RewriteStatus exposes the three branches the pipeline uses."""

    def test_values(self) -> None:
        assert RewriteStatus.OK.value == "ok"
        assert RewriteStatus.UNRESOLVABLE.value == "unresolvable"
        assert RewriteStatus.FALLBACK.value == "fallback"


class TestRewriteResultModel:
    """RewriteResult carries status, effective query, and optional token usage."""

    def test_shape(self) -> None:
        required = {"status", "query", "token_usage"}
        assert required.issubset(RewriteResult.model_fields.keys())

    def test_token_usage_optional(self) -> None:
        result = RewriteResult(status=RewriteStatus.FALLBACK, query="원문", token_usage=None)
        assert result.token_usage is None


class TestRewriteQueryOk:
    """Normal rewrite: LLM returns a rewritten single-line query."""

    @pytest.mark.asyncio
    async def test_returns_ok_with_rewritten_query(self) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("타이레놀과 술을 같이 먹어도 되나요?"),
        )

        history = [
            {"role": "user", "content": "타이레놀 부작용 알려줘"},
            {"role": "assistant", "content": "타이레놀의 부작용은..."},
        ]
        result = await gen.rewrite_query(history=history, current_query="그 약과 술 같이 먹으면?")

        assert result.status == RewriteStatus.OK
        assert result.query == "타이레놀과 술을 같이 먹어도 되나요?"
        assert isinstance(result.token_usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_strips_surrounding_whitespace_and_quotes(self) -> None:
        """LLMs sometimes wrap output in quotes or add trailing newlines."""
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response('  "타이레놀 부작용" \n'),
        )

        result = await gen.rewrite_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.OK
        assert result.query == "타이레놀 부작용"


class TestRewriteQueryUnresolvable:
    """LLM signals it cannot resolve the reference with UNRESOLVABLE sentinel."""

    @pytest.mark.asyncio
    async def test_detects_unresolvable_sentinel(self) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("UNRESOLVABLE"),
        )

        result = await gen.rewrite_query(history=[], current_query="그 약 부작용 알려줘")
        assert result.status == RewriteStatus.UNRESOLVABLE
        assert result.query == "그 약 부작용 알려줘"  # original preserved
        assert isinstance(result.token_usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_case_insensitive_sentinel_with_surrounding_noise(self) -> None:
        """Match UNRESOLVABLE even if LLM adds stray punctuation/casing."""
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("unresolvable."),
        )

        result = await gen.rewrite_query(history=[], current_query="그 약 부작용")
        assert result.status == RewriteStatus.UNRESOLVABLE


class TestRewriteQueryFallback:
    """Technical failures fall back to the original query with no usage info."""

    @pytest.mark.asyncio
    async def test_api_exception_falls_back(self) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("timeout"))

        result = await gen.rewrite_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.FALLBACK
        assert result.query == "타이레놀 부작용"
        assert result.token_usage is None

    @pytest.mark.asyncio
    async def test_empty_llm_response_falls_back(self) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(return_value=_mock_openai_response(""))

        result = await gen.rewrite_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.FALLBACK
        assert result.query == "타이레놀 부작용"

    @pytest.mark.asyncio
    async def test_missing_client_falls_back(self) -> None:
        """When OPENAI_API_KEY is absent, client is None and rewrite is skipped."""
        gen = RAGGenerator()
        gen.client = None

        result = await gen.rewrite_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.FALLBACK
        assert result.query == "타이레놀 부작용"
        assert result.token_usage is None


@pytest.fixture
def _enable_ai_worker_propagation() -> object:
    """Temporarily allow ai_worker.* logs to reach pytest's caplog handler.

    `app/core/logger.py` sets propagate=False on the "ai_worker" logger to
    stop uvicorn's root handler from double-printing bare-format lines in
    production. caplog, however, attaches its capture handler on root and
    relies on propagation, so without this override the log assertions see
    zero records. Scope is per-test to preserve the production default.
    """
    import logging

    logger = logging.getLogger("ai_worker")
    original = logger.propagate
    logger.propagate = True
    try:
        yield
    finally:
        logger.propagate = original


@pytest.mark.usefixtures("_enable_ai_worker_propagation")
class TestRewriteQueryLogging:
    """Key status transitions must emit structured [RAG] log lines."""

    @pytest.mark.asyncio
    async def test_logs_ok_path(self, caplog: pytest.LogCaptureFixture) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("타이레놀과 술"),
        )

        with caplog.at_level("INFO", logger="ai_worker.utils.rag"):
            await gen.rewrite_query(history=[], current_query="그 약과 술")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite: ok" in messages

    @pytest.mark.asyncio
    async def test_logs_unresolvable_path(self, caplog: pytest.LogCaptureFixture) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("UNRESOLVABLE"),
        )

        with caplog.at_level("WARNING", logger="ai_worker.utils.rag"):
            await gen.rewrite_query(history=[], current_query="그 약")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite: unresolvable" in messages

    @pytest.mark.asyncio
    async def test_logs_api_error_path(self, caplog: pytest.LogCaptureFixture) -> None:
        gen = RAGGenerator()
        gen.client = MagicMock()
        gen.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

        with caplog.at_level("ERROR", logger="ai_worker.utils.rag"):
            await gen.rewrite_query(history=[], current_query="타이레놀 부작용")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite:" in messages
        assert "api_error" in messages or "fallback" in messages
