"""RAG service package — 옵션 C 이후의 잔여 모듈만 export.

옵션 C 에서 RAG retrieval 은 ai-worker 의 Router LLM tool dispatch 로 흡수
되어 FastAPI 측에서는 더 이상 RAGPipeline / get_rag_pipeline 같은 진입점이
없다. 본 패키지의 잔여 책임:

- ``app.services.rag.config`` — 임베딩 모델 이름·차원 (모델·DTO 가 참조)
- ``app.services.rag.retrievers.hybrid`` — ai-worker 가 import 해 사용
- ``app.services.rag.providers.rq_llm.RQRAGGenerator`` —
  ``session_compact_service`` 가 ``summarize_messages`` 만 사용
- ``app.services.rag.protocols`` — ``EmbeddingProvider`` / ``Retriever``
  Protocol 정의 (HybridRetriever 시그니처용)

Public 진입점은 explicit submodule path 로만 노출한다.
"""
