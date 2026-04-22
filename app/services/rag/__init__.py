"""RAG service package.

The top-level namespace is intentionally minimal so that the leaf
`config` module (embedding model name, dimensions) can be imported by
lower layers (`app.models.medicine_info`, `app.dtos.rag`) without
triggering the full pipeline graph. Public components live at explicit
submodule paths:

    from app.services.rag.pipeline import RAGPipeline
    from app.services.rag.retrievers.hybrid import HybridRetriever
    from app.services.rag.providers.sentence_transformer import (
        SentenceTransformerProvider,
        get_sentence_transformer_provider,
    )
"""

_pipeline: "RAGPipeline | None" = None  # noqa: F821  # forward ref resolved lazily


async def get_rag_pipeline() -> "RAGPipeline":  # noqa: F821  # forward ref resolved lazily
    """Get or create the global RAGPipeline instance.

    Builds the pipeline on first call: initializes the embedding model,
    wires the hybrid retriever, intent classifier, tool router, and
    RAG generator. Subsequent calls return the cached instance.
    """
    global _pipeline

    if _pipeline is None:
        from ai_worker.utils.rag import RAGGenerator
        from app.services.rag.intent.classifier import IntentClassifier
        from app.services.rag.pipeline import RAGPipeline
        from app.services.rag.providers.sentence_transformer import get_sentence_transformer_provider
        from app.services.rag.retrievers.hybrid import HybridRetriever
        from app.services.rag.tools import ToolRouter

        provider = await get_sentence_transformer_provider()
        _pipeline = RAGPipeline(
            embedding_provider=provider,
            retriever=HybridRetriever(embedding_provider=provider),
            intent_classifier=IntentClassifier(),
            tool_router=ToolRouter(),
            rag_generator=RAGGenerator(),
        )

    return _pipeline


__all__ = ["get_rag_pipeline"]
