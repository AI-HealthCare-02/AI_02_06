"""Tests for RAGPipeline - full pipeline flow with mocks."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dtos.rag import RAGResponse
from app.services.rag.intent.intents import IntentType
from app.services.rag.pipeline import RAGPipeline


def _make_pipeline(
    intent: IntentType = IntentType.MEDICATION_INFO,
    search_results: list | None = None,
    llm_answer: str = "테스트 답변입니다.",
) -> RAGPipeline:
    """Create a RAGPipeline with mocked dependencies."""
    mock_provider = MagicMock()
    mock_provider.dimensions = 768
    mock_provider.encode_single = AsyncMock(return_value=[0.1] * 768)
    mock_provider.encode_batch = AsyncMock(return_value=[[0.1] * 768])

    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=search_results or [])

    mock_classifier = MagicMock()
    mock_classifier.classify = MagicMock(return_value=intent)

    mock_tool_router = MagicMock()
    mock_tool_router.execute = AsyncMock(return_value=llm_answer)

    mock_generator = MagicMock()
    mock_generator.generate_chat_response = AsyncMock(return_value=llm_answer)

    return RAGPipeline(
        embedding_provider=mock_provider,
        retriever=mock_retriever,
        intent_classifier=mock_classifier,
        tool_router=mock_tool_router,
        rag_generator=mock_generator,
    )


class TestRAGPipelineInit:
    """Test RAGPipeline initialization."""

    def test_pipeline_requires_embedding_provider(self) -> None:
        """RAGPipeline must require embedding_provider."""
        with pytest.raises(TypeError):
            RAGPipeline()  # type: ignore[call-arg]

    def test_pipeline_stores_dependencies(self) -> None:
        """RAGPipeline must store all injected dependencies."""
        pipeline = _make_pipeline()
        assert hasattr(pipeline, "embedding_provider")
        assert hasattr(pipeline, "retriever")
        assert hasattr(pipeline, "intent_classifier")
        assert hasattr(pipeline, "tool_router")


class TestRAGPipelineAsk:
    """Test RAGPipeline.ask() method."""

    @pytest.mark.asyncio
    async def test_ask_returns_rag_response(self) -> None:
        """ask() must return a RAGResponse instance."""
        pipeline = _make_pipeline()
        result = await pipeline.ask(question="타이레놀 부작용이 뭐야?", history=[])
        assert isinstance(result, RAGResponse)

    @pytest.mark.asyncio
    async def test_ask_response_has_answer(self) -> None:
        """RAGResponse must contain a non-empty answer."""
        pipeline = _make_pipeline(llm_answer="타이레놀 부작용은 위장장애입니다.")
        result = await pipeline.ask(question="타이레놀 부작용이 뭐야?", history=[])
        assert result.answer
        assert isinstance(result.answer, str)

    @pytest.mark.asyncio
    async def test_ask_calls_intent_classifier(self) -> None:
        """ask() must call intent_classifier.classify()."""
        pipeline = _make_pipeline()
        await pipeline.ask(question="타이레놀 부작용이 뭐야?", history=[])
        pipeline.intent_classifier.classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_medication_info_calls_retriever(self) -> None:
        """MEDICATION_INFO intent must trigger retriever.retrieve()."""
        pipeline = _make_pipeline(intent=IntentType.MEDICATION_INFO)
        await pipeline.ask(question="타이레놀 부작용이 뭐야?", history=[])
        pipeline.retriever.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_out_of_scope_skips_retriever(self) -> None:
        """OUT_OF_SCOPE intent must not call retriever.retrieve()."""
        pipeline = _make_pipeline(intent=IntentType.OUT_OF_SCOPE)
        await pipeline.ask(question="주식 추천해줘", history=[])
        pipeline.retriever.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_response_has_processing_time(self) -> None:
        """RAGResponse must include processing_time_ms."""
        pipeline = _make_pipeline()
        result = await pipeline.ask(question="test", history=[])
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_ask_response_has_confidence_score(self) -> None:
        """RAGResponse must include confidence_score between 0 and 1."""
        pipeline = _make_pipeline()
        result = await pipeline.ask(question="test", history=[])
        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_ask_with_history_passes_history_to_generator(self) -> None:
        """ask() must pass conversation history to the generator."""
        pipeline = _make_pipeline()
        history = [{"role": "user", "content": "이전 질문"}]
        await pipeline.ask(question="test", history=history)
        pipeline.rag_generator.generate_chat_response.assert_called_once()
        call_args = pipeline.rag_generator.generate_chat_response.call_args
        passed_messages = call_args[0][0] if call_args[0] else call_args[1].get("messages", [])
        assert any(m["content"] == "이전 질문" for m in passed_messages)

    @pytest.mark.asyncio
    async def test_ask_general_chat_skips_retriever(self) -> None:
        """GENERAL_CHAT intent must not call retriever.retrieve()."""
        pipeline = _make_pipeline(intent=IntentType.GENERAL_CHAT)
        await pipeline.ask(question="안녕", history=[])
        pipeline.retriever.retrieve.assert_not_called()
