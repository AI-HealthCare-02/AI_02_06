"""RAG service package.

Public interface for the RAG pipeline.
"""

from app.services.rag.intent.classifier import IntentClassifier
from app.services.rag.intent.intents import IntentType
from app.services.rag.pipeline import RAGPipeline
from app.services.rag.protocols import EmbeddingProvider, Retriever
from app.services.rag.providers.sentence_transformer import SentenceTransformerProvider
from app.services.rag.retrievers.hybrid import HybridRetriever
from app.services.rag.tools import ToolRouter

_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the global RAGPipeline instance.

    Returns:
        Configured RAGPipeline with all dependencies injected.
    """
    global _pipeline

    if _pipeline is None:
        from ai_worker.utils.rag import RAGGenerator

        provider = SentenceTransformerProvider()
        _pipeline = RAGPipeline(
            embedding_provider=provider,
            retriever=HybridRetriever(embedding_provider=provider),
            intent_classifier=IntentClassifier(),
            tool_router=ToolRouter(),
            rag_generator=RAGGenerator(),
        )

    return _pipeline


__all__ = [
    "EmbeddingProvider",
    "HybridRetriever",
    "IntentClassifier",
    "IntentType",
    "RAGPipeline",
    "Retriever",
    "SentenceTransformerProvider",
    "ToolRouter",
    "get_rag_pipeline",
]
