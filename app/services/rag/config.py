"""Centralized embedding configuration for the RAG pipeline.

Single source of truth for the embedding model and its vector dimensions.
PLAN.md (feature/RAG) §0 — OpenAI text-embedding-3-large (3072d) 사용.
ko-sroberta (jhgan/ko-sroberta-multitask, 768d) 는 폐기.
"""

EMBEDDING_MODEL_NAME: str = "text-embedding-3-large"
EMBEDDING_DIMENSIONS: int = 3072
