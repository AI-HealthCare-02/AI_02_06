"""RAG service package.

The top-level namespace is intentionally minimal so that the leaf
`config` module (embedding model name, dimensions) can be imported by
lower layers (`app.models.medicine_info`, `app.dtos.rag`) without
triggering the full pipeline graph. Public components live at explicit
submodule paths:

    from app.services.rag.pipeline import RAGPipeline
    from app.services.rag.retrievers.hybrid import HybridRetriever
    from app.services.rag.providers.rq_embedding import RQEmbeddingProvider
    from app.services.rag.providers.rq_llm import RQRAGGenerator
"""

_pipeline: "RAGPipeline | None" = None  # noqa: F821  # forward ref resolved lazily


async def get_rag_pipeline() -> "RAGPipeline":  # noqa: F821  # forward ref resolved lazily
    """Get or create the global RAGPipeline instance.

    Wires the RAG pipeline with AI-Worker-backed embedding and LLM
    providers. FastAPI never loads the embedding model or constructs an
    OpenAI client; instead both paths enqueue RQ jobs to the "ai" queue
    and await results.
    """
    global _pipeline

    if _pipeline is None:
        # 의도적 lazy import — top-level 로 올리면 ``app.services.rag`` 패키지의
        # 초기화 단계에서 ``app.dtos.rag`` → ``app.services.rag.config`` 의 순환
        # import 가 발생한다. CLAUDE.md §8.5 의 lazy import 금지 정책 예외 (circular
        # 회피 + 무거운 RAGPipeline graph 의 startup-trigger 최소화).
        from rq import Queue

        from app.core.config import config
        from app.core.redis_client import make_sync_redis
        from app.repositories.profile_repository import ProfileRepository
        from app.services.rag.intent.classifier import IntentClassifier
        from app.services.rag.pipeline import RAGPipeline
        from app.services.rag.providers.rq_embedding import RQEmbeddingProvider
        from app.services.rag.providers.rq_llm import RQRAGGenerator
        from app.services.rag.retrievers.hybrid import HybridRetriever
        from app.services.rag.tools import ToolRouter

        redis_conn = make_sync_redis(config.REDIS_URL)
        ai_queue = Queue("ai", connection=redis_conn)

        embedding_provider = RQEmbeddingProvider(queue=ai_queue)
        rag_generator = RQRAGGenerator(queue=ai_queue)

        _pipeline = RAGPipeline(
            embedding_provider=embedding_provider,
            retriever=HybridRetriever(embedding_provider=embedding_provider),
            intent_classifier=IntentClassifier(),
            tool_router=ToolRouter(),
            rag_generator=rag_generator,
            profile_repository=ProfileRepository(),
        )

    return _pipeline


__all__ = ["get_rag_pipeline"]
