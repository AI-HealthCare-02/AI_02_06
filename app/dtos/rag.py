"""RAG (Retrieval-Augmented Generation) DTO models.

This module defines data transfer objects for the RAG pipeline,
including search filters, search results, and RAG responses.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.vector_models import ChunkType, DocumentChunk, UserCondition


class SearchFilters(BaseModel):
    """Search filters for metadata-based filtering."""

    user_conditions: list[UserCondition] = Field(default_factory=list)
    medicine_names: list[str] = Field(default_factory=list)
    chunk_types: list[ChunkType] = Field(default_factory=list)
    date_range: tuple[str, str] | None = None


class SearchResult(BaseModel):
    """Represents a single search result with relevance scores."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    chunk: DocumentChunk
    vector_score: float
    keyword_score: float
    metadata_score: float
    final_score: float


class RAGResponse(BaseModel):
    """Response from the RAG pipeline."""

    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float
    search_results_count: int
    processing_time_ms: int
