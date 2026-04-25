"""Centralized embedding configuration for the RAG pipeline.

Single source of truth for the embedding model and its vector dimensions.
Swapping models requires:
  1. Updating the constants below.
  2. Running an Aerich migration that alters the
     medicine_info.embedding column to the new vector(N) dimension.
  3. Re-running the seeding script to repopulate embeddings.
"""

EMBEDDING_MODEL_NAME: str = "jhgan/ko-sroberta-multitask"
EMBEDDING_DIMENSIONS: int = 768
