"""Embedding service for Korean pharmaceutical documents."""

import asyncio
import hashlib
import logging
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Default Korean-optimized sentence transformer model.
# Replace this constant to upgrade the embedding model globally.
_DEFAULT_MODEL = "jhgan/ko-sroberta-multitask"


class EmbeddingService:
    """Service for generating embeddings from Korean pharmaceutical texts."""

    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask"):
        """Initialize embedding service with Korean-optimized model.

        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        self.dimensions = 768  # Default for ko-sroberta-multitask
        self._model_config: dict[str, Any] | None = None

    async def initialize(self) -> None:
        """Initialize the embedding model asynchronously."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")

            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, SentenceTransformer, self.model_name)

            # Update dimensions based on actual model
            if hasattr(self.model, "get_sentence_embedding_dimension"):
                self.dimensions = self.model.get_sentence_embedding_dimension()

            # Store model configuration
            self._model_config = {
                "model_name": self.model_name,
                "dimensions": self.dimensions,
                "max_tokens": 512,  # Default for most Korean models
                "language_support": ["ko"],
            }

            logger.info(f"Embedding model loaded successfully. Dimensions: {self.dimensions}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def preprocess_korean_text(self, text: str) -> str:
        """Preprocess Korean pharmaceutical text for embedding.

        Args:
            text: Raw Korean text

        Returns:
            Preprocessed text ready for embedding
        """
        if not text:
            return ""

        # Basic cleaning
        cleaned = text.strip()

        # Remove excessive whitespace
        cleaned = " ".join(cleaned.split())

        # Normalize Korean pharmaceutical terms
        cleaned = self._normalize_pharmaceutical_terms(cleaned)

        return cleaned

    def _normalize_pharmaceutical_terms(self, text: str) -> str:
        """Normalize common pharmaceutical terms for consistency.

        Args:
            text: Input text

        Returns:
            Text with normalized pharmaceutical terms
        """
        # Common term normalizations
        normalizations = {
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

        for original, normalized in normalizations.items():
            text = text.replace(original, normalized)

        return text

    async def encode_single(self, text: str) -> list[float]:
        """Encode a single text into embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector as list of floats

        Raises:
            RuntimeError: If model is not initialized
        """
        if self.model is None:
            raise RuntimeError("Embedding model not initialized. Call initialize() first.")

        if not text:
            return [0.0] * self.dimensions

        # Preprocess text
        processed_text = self.preprocess_korean_text(text)

        # Generate embedding in thread pool
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self.model.encode, processed_text)

        # Convert to list and normalize
        embedding_list = embedding.tolist()
        normalized_embedding = self._normalize_vector(embedding_list)

        return normalized_embedding

    async def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Encode multiple texts in batches for efficiency.

        Args:
            texts: List of texts to encode
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        if self.model is None:
            raise RuntimeError("Embedding model not initialized. Call initialize() first.")

        if not texts:
            return []

        # Preprocess all texts
        processed_texts = [self.preprocess_korean_text(text) for text in texts]

        # Process in batches
        embeddings = []
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i : i + batch_size]

            # Generate embeddings for batch
            loop = asyncio.get_event_loop()
            batch_embeddings = await loop.run_in_executor(None, self.model.encode, batch)

            # Convert to list and normalize
            for embedding in batch_embeddings:
                embedding_list = embedding.tolist()
                normalized_embedding = self._normalize_vector(embedding_list)
                embeddings.append(normalized_embedding)

        return embeddings

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        """Normalize vector to unit length for cosine similarity optimization.

        Args:
            vector: Input vector

        Returns:
            L2 normalized vector
        """
        if not vector:
            return vector

        # Convert to numpy for efficient computation
        np_vector = np.array(vector)

        # Calculate L2 norm
        norm = np.linalg.norm(np_vector)

        # Avoid division by zero
        if norm == 0:
            return vector

        # Normalize and convert back to list
        normalized = np_vector / norm
        return normalized.tolist()

    def calculate_similarity(self, vector1: list[float], vector2: list[float]) -> float:
        """Calculate cosine similarity between two normalized vectors.

        Args:
            vector1: First vector (should be normalized)
            vector2: Second vector (should be normalized)

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(vector1) != len(vector2):
            raise ValueError("Vectors must have the same dimensions")

        # For normalized vectors, cosine similarity = dot product
        similarity = np.dot(vector1, vector2)

        # Ensure result is within valid range
        return float(np.clip(similarity, -1.0, 1.0))

    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the current embedding model.

        Returns:
            Dictionary containing model information
        """
        if self._model_config is None:
            await self.initialize()

        return self._model_config.copy()

    def generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash for content deduplication.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


# Global embedding service instance
_embedding_service: EmbeddingService | None = None


async def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service instance.

    Returns:
        Initialized embedding service
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name=_DEFAULT_MODEL)
        await _embedding_service.initialize()

    return _embedding_service


async def cleanup_embedding_service() -> None:
    """Cleanup global embedding service."""
    global _embedding_service
    if _embedding_service is not None:
        # Model cleanup would go here if needed
        _embedding_service = None
