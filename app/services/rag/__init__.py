"""RAG service package — feature/RAG 4단 파이프라인 잔여 모듈.

본 패키지의 책임:

- ``app.services.rag.config`` — 임베딩 모델 이름·차원 (text-embedding-3-large, 3072d)
- ``app.services.rag.openai_embedding`` — query 측 OpenAI Embedding 호출
- ``app.services.rag.retrievers.hybrid`` — pgvector + tsvector RRF 융합
- ``app.services.rag.retrievers.rrf`` — 2단 RRF (intra + cross)
- ``app.services.rag.protocols`` — ``EmbeddingProvider`` / ``Retriever`` Protocol 정의

Public 진입점은 explicit submodule path 로만 노출한다.
"""
