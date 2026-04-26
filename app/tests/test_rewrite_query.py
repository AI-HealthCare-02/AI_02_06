"""쿼리 재작성 LLM 단위 테스트.

``ai_worker/domains/rag/query_rewriter.py::rewrite_user_query`` 가 다중 턴
한국어 질의를 self-contained 한 단일 쿼리로 변환하면서 ok / unresolvable /
fallback 세 가지 상태로 분기되는 계약을 검증한다.

이전에는 ``RAGGenerator`` 클래스의 메서드였으나 도메인 분해에 따라 함수형
모듈로 이전됐다. 테스트는 ``monkeypatch`` 로 ``get_openai_client`` 를 가짜로
교체해 OpenAI 호출 없이 응답 분기를 시뮬레이션한다.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_worker.domains.rag import query_rewriter
from app.dtos.rag import RewriteResult, RewriteStatus, TokenUsage


def _mock_openai_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 20) -> MagicMock:
    """openai.ChatCompletion 형태의 MagicMock 을 만든다."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, completion_mock: AsyncMock | None) -> None:
    """``get_openai_client`` 를 가짜 클라이언트(또는 None)로 교체."""
    if completion_mock is None:
        monkeypatch.setattr(query_rewriter, "get_openai_client", lambda: None)
        return
    fake_client = MagicMock()
    fake_client.chat.completions.create = completion_mock
    monkeypatch.setattr(query_rewriter, "get_openai_client", lambda: fake_client)


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
    async def test_returns_ok_with_rewritten_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_client(
            monkeypatch,
            AsyncMock(return_value=_mock_openai_response("타이레놀과 술을 같이 먹어도 되나요?")),
        )
        history = [
            {"role": "user", "content": "타이레놀 부작용 알려줘"},
            {"role": "assistant", "content": "타이레놀의 부작용은..."},
        ]
        result = await query_rewriter.rewrite_user_query(
            history=history,
            current_query="그 약과 술 같이 먹으면?",
        )
        assert result.status == RewriteStatus.OK
        assert result.query == "타이레놀과 술을 같이 먹어도 되나요?"
        assert isinstance(result.token_usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_strips_surrounding_whitespace_and_quotes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMs sometimes wrap output in quotes or add trailing newlines."""
        _install_fake_client(
            monkeypatch,
            AsyncMock(return_value=_mock_openai_response('  "타이레놀 부작용" \n')),
        )
        result = await query_rewriter.rewrite_user_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.OK
        assert result.query == "타이레놀 부작용"


class TestRewriteQueryUnresolvable:
    """LLM signals it cannot resolve the reference with UNRESOLVABLE sentinel."""

    @pytest.mark.asyncio
    async def test_detects_unresolvable_sentinel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_client(monkeypatch, AsyncMock(return_value=_mock_openai_response("UNRESOLVABLE")))
        result = await query_rewriter.rewrite_user_query(history=[], current_query="그 약 부작용 알려줘")
        assert result.status == RewriteStatus.UNRESOLVABLE
        assert result.query == "그 약 부작용 알려줘"  # original preserved
        assert isinstance(result.token_usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_case_insensitive_sentinel_with_surrounding_noise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Match UNRESOLVABLE even if LLM adds stray punctuation/casing."""
        _install_fake_client(monkeypatch, AsyncMock(return_value=_mock_openai_response("unresolvable.")))
        result = await query_rewriter.rewrite_user_query(history=[], current_query="그 약 부작용")
        assert result.status == RewriteStatus.UNRESOLVABLE


class TestRewriteQueryFallback:
    """Technical failures fall back to the original query with no usage info."""

    @pytest.mark.asyncio
    async def test_api_exception_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_client(monkeypatch, AsyncMock(side_effect=RuntimeError("timeout")))
        result = await query_rewriter.rewrite_user_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.FALLBACK
        assert result.query == "타이레놀 부작용"
        assert result.token_usage is None

    @pytest.mark.asyncio
    async def test_empty_llm_response_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_client(monkeypatch, AsyncMock(return_value=_mock_openai_response("")))
        result = await query_rewriter.rewrite_user_query(history=[], current_query="타이레놀 부작용")
        assert result.status == RewriteStatus.FALLBACK
        assert result.query == "타이레놀 부작용"

    @pytest.mark.asyncio
    async def test_missing_client_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When OPENAI_API_KEY is absent, get_openai_client returns None and rewrite is skipped."""
        _install_fake_client(monkeypatch, None)
        result = await query_rewriter.rewrite_user_query(history=[], current_query="타이레놀 부작용")
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
    async def test_logs_ok_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _install_fake_client(
            monkeypatch,
            AsyncMock(return_value=_mock_openai_response("타이레놀과 술")),
        )
        with caplog.at_level("INFO", logger="ai_worker.domains.rag.query_rewriter"):
            await query_rewriter.rewrite_user_query(history=[], current_query="그 약과 술")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite: ok" in messages

    @pytest.mark.asyncio
    async def test_logs_unresolvable_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _install_fake_client(monkeypatch, AsyncMock(return_value=_mock_openai_response("UNRESOLVABLE")))
        with caplog.at_level("WARNING", logger="ai_worker.domains.rag.query_rewriter"):
            await query_rewriter.rewrite_user_query(history=[], current_query="그 약")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite: unresolvable" in messages

    @pytest.mark.asyncio
    async def test_logs_api_error_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _install_fake_client(monkeypatch, AsyncMock(side_effect=RuntimeError("boom")))
        with caplog.at_level("ERROR", logger="ai_worker.domains.rag.query_rewriter"):
            await query_rewriter.rewrite_user_query(history=[], current_query="타이레놀 부작용")

        messages = " | ".join(r.getMessage() for r in caplog.records)
        assert "[RAG] rewrite:" in messages
        assert "api_error" in messages or "fallback" in messages
