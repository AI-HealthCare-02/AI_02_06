"""RAG (Retrieval-Augmented Generation) DTO models.

Data transfer objects for the MedicineInfo-backed RAG pipeline:
- SearchFilters: metadata filters applied at retrieval time.
- SearchResult: a single ranked MedicineInfo match.
- RetrievalMetadata: summary of the retrieval stage (for debug/cache keys).
- TokenUsage: LLM token usage for the assistant turn.
- ChatCompletion: RAGGenerator output (answer + optional token usage).
- RewriteStatus / RewriteResult: LLM query-rewrite outcome.
- RAGResponse: the final pipeline payload returned to the API layer.
"""

from enum import StrEnum
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


class RetrievalMetadata(BaseModel):
    """Structured summary of the retrieval stage.

    Persisted on the user turn's `messages.metadata` to support multi-turn
    pronoun resolution and cache key construction.
    """

    medicine_names: list[str] = Field(default_factory=list, description="Top-k medicine names")
    medicine_usages: list[str] = Field(default_factory=list, description="Top-k medicine usages (categories)")
    top_similarity: float | None = Field(None, description="Cosine similarity of the top-1 match")
    vector_score: float | None = Field(None, description="Top-1 vector similarity score")
    keyword_score: float | None = Field(None, description="Top-1 keyword score")
    final_score: float | None = Field(None, description="Top-1 final weighted score")


class TokenUsage(BaseModel):
    """LLM token usage, mirroring OpenAI's response.usage."""

    model: str = Field(..., description="LLM model identifier")
    prompt_tokens: int = Field(..., description="Tokens sent in the prompt")
    completion_tokens: int = Field(..., description="Tokens generated in the completion")
    total_tokens: int = Field(..., description="Sum of prompt and completion tokens")


class ChatCompletion(BaseModel):
    """RAGGenerator output: the text answer plus optional token usage."""

    answer: str = Field(..., description="Generated assistant reply")
    token_usage: TokenUsage | None = Field(None, description="LLM token usage when available")


class RewriteStatus(StrEnum):
    """Outcome of the LLM query-rewrite stage."""

    OK = "ok"
    UNRESOLVABLE = "unresolvable"
    FALLBACK = "fallback"


class RewriteResult(BaseModel):
    """Structured result of RAGGenerator.rewrite_query."""

    status: RewriteStatus = Field(..., description="Rewrite outcome category")
    query: str = Field(..., description="Query to use downstream (rewritten on ok, original otherwise)")
    token_usage: TokenUsage | None = Field(None, description="LLM token usage when the rewrite call succeeded")


class RAGResponse(BaseModel):
    """Top-level RAG pipeline response consumed by MessageService."""

    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float
    search_results_count: int
    processing_time_ms: int

    # Debug/audit fields persisted on messages.metadata
    intent: str = Field(..., description="Classified intent for this turn")
    query_keywords: list[str] = Field(default_factory=list, description="Keywords extracted from the user query")
    retrieval: RetrievalMetadata = Field(default_factory=RetrievalMetadata, description="Retrieval stage summary")
    token_usage: TokenUsage | None = Field(None, description="LLM token usage when available")
