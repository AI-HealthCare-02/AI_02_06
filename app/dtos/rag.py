"""RAG (Retrieval-Augmented Generation) DTO models.

Data transfer objects for the MedicineInfo-backed RAG pipeline:
- SearchFilters: metadata filters applied at retrieval time.
- SearchResult: a single ranked MedicineInfo match.
- RAGResponse: the final answer payload returned to the API layer.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.medicine_info import MedicineInfo


class SearchFilters(BaseModel):
    """Retrieval-time filters for medicine_info rows."""

    medicine_names: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """A single scored MedicineInfo match from the retriever."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    medicine: MedicineInfo
    vector_score: float
    keyword_score: float
    final_score: float


class RAGResponse(BaseModel):
    """Top-level RAG pipeline response consumed by MessageService."""

    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float
    search_results_count: int
    processing_time_ms: int
