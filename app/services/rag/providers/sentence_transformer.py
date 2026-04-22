"""SentenceTransformer-based embedding provider.

Implements EmbeddingProvider using a local Korean-optimized
sentence transformer model.
"""

import asyncio
import hashlib
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from app.services.rag.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

# Common Korean pharmaceutical term normalizations for embedding quality.
_TERM_NORMALIZATIONS: dict[str, str] = {
    "효능·효과": "효능 효과",
    "용법·용량": "용법 용량",
    "사용상의주의사항": "사용상 주의사항",
    "사용상주의사항": "사용상 주의사항",
    "약물상호작용": "약물 상호작용",
    "mg/kg": "mg per kg",
    "1일": "하루",
    "2회": "두번",
    "3회": "세번",
    "4회": "네번",
}


class SentenceTransformerProvider:
    """EmbeddingProvider using a local SentenceTransformer model.

    Loads the model lazily on first use via initialize().
    Normalizes vectors to unit length for cosine similarity.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        """Initialize provider with model name.

        Args:
            model_name: HuggingFace model identifier.
        """
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        self._dimensions: int = EMBEDDING_DIMENSIONS

    @property
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: int) -> None:
        """Set embedding vector dimensions.

        Args:
            value: New dimension value.
        """
        self._dimensions = value

    async def initialize(self) -> None:
        """Load the embedding model asynchronously.

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            logger.info("Loading embedding model: %s", self.model_name)
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, SentenceTransformer, self.model_name)

            if hasattr(self.model, "get_embedding_dimension"):
                self._dimensions = self.model.get_embedding_dimension()
            elif hasattr(self.model, "get_sentence_embedding_dimension"):
                self._dimensions = self.model.get_sentence_embedding_dimension()

            logger.info("Embedding model loaded. Dimensions: %d", self._dimensions)
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            raise

    def preprocess(self, text: str) -> str:
        """Preprocess Korean pharmaceutical text for embedding.

        Args:
            text: Raw input text.

        Returns:
            Cleaned and normalized text.
        """
        if not text:
            return ""
        cleaned = " ".join(text.strip().split())
        for original, normalized in _TERM_NORMALIZATIONS.items():
            cleaned = cleaned.replace(original, normalized)
        return cleaned

    async def encode_single(self, text: str) -> list[float]:
        """Encode a single text into a normalized embedding vector.

        Args:
            text: Input text to encode.

        Returns:
            L2-normalized embedding vector.

        Raises:
            RuntimeError: If model is not initialized.
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")

        if not text:
            return [0.0] * self._dimensions

        processed = self.preprocess(text)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self.model.encode, processed)
        return self._normalize(embedding.tolist())

    async def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Encode multiple texts in batches.

        Args:
            texts: List of input texts.
            batch_size: Number of texts per batch.

        Returns:
            List of L2-normalized embedding vectors.

        Raises:
            RuntimeError: If model is not initialized.
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")

        if not texts:
            return []

        processed = [self.preprocess(t) for t in texts]
        embeddings: list[list[float]] = []

        for i in range(0, len(processed), batch_size):
            batch = processed[i : i + batch_size]
            loop = asyncio.get_event_loop()
            batch_embeddings = await loop.run_in_executor(None, self.model.encode, batch)
            embeddings.extend(self._normalize(emb.tolist()) for emb in batch_embeddings)

        return embeddings

    def _normalize(self, vector: list[float]) -> list[float]:
        """L2-normalize a vector for cosine similarity optimization.

        Args:
            vector: Input vector.

        Returns:
            Unit-length vector.
        """
        np_vec = np.array(vector)
        norm = np.linalg.norm(np_vec)
        if norm == 0:
            return vector
        return (np_vec / norm).tolist()

    def generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash for content deduplication.

        Args:
            content: Content to hash.

        Returns:
            SHA256 hex digest.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


# Global provider instance
_provider: SentenceTransformerProvider | None = None


async def get_sentence_transformer_provider() -> SentenceTransformerProvider:
    """Get or create the global SentenceTransformerProvider instance.

    Returns:
        Initialized SentenceTransformerProvider.
    """
    global _provider

    if _provider is None:
        _provider = SentenceTransformerProvider()
        await _provider.initialize()

    return _provider
