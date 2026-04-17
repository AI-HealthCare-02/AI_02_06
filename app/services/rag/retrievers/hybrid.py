"""Hybrid retriever combining vector similarity and keyword matching.

Implements the Retriever protocol using pgvector for vector search
and keyword scoring for hybrid ranking.
"""

import logging
import re
import time

from tortoise import connections

from app.dtos.rag import SearchFilters, SearchResult
from app.models.vector_models import DocumentChunk, SearchQuery
from app.services.rag.protocols import EmbeddingProvider

logger = logging.getLogger(__name__)

_STOP_WORDS: frozenset[str] = frozenset({
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "에서",
    "로",
    "으로",
    "와",
    "과",
    "하고",
})


class HybridRetriever:
    """Retriever combining pgvector similarity search with keyword scoring.

    Weights are normalized so vector_weight + keyword_weight == 1.0.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        """Initialize hybrid retriever.

        Args:
            embedding_provider: Provider used for query embedding.
            vector_weight: Weight for vector similarity score.
            keyword_weight: Weight for keyword matching score.
        """
        self.embedding_provider = embedding_provider
        total = vector_weight + keyword_weight
        self.vector_weight = vector_weight / total
        self.keyword_weight = keyword_weight / total

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        filters: SearchFilters,
        limit: int,
    ) -> list[SearchResult]:
        """Retrieve relevant chunks using hybrid search.

        Args:
            query: Original query text for keyword scoring.
            query_embedding: Pre-computed query embedding vector.
            filters: Metadata filters to apply.
            limit: Maximum number of results.

        Returns:
            List of SearchResult sorted by final_score descending.
        """
        start_time = time.time()

        vector_results = await self._vector_search(query_embedding, filters, limit * 3)

        if not vector_results:
            return []

        query_keywords = self._extract_keywords(query)
        results = []

        for chunk, vector_score in vector_results:
            keyword_score = self.calculate_keyword_score(
                query_keywords=query_keywords,
                chunk_keywords=chunk.keywords or [],
                chunk_content=chunk.content,
            )
            final_score = self.vector_weight * vector_score + self.keyword_weight * keyword_score
            results.append(
                SearchResult(
                    chunk=chunk,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    metadata_score=0.0,
                    final_score=final_score,
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        final = results[:limit]

        duration_ms = int((time.time() - start_time) * 1000)
        await self._log_query(query, query_embedding, filters, final, duration_ms)

        return final

    async def _vector_search(
        self,
        query_embedding: list[float],
        filters: SearchFilters,
        limit: int,
        similarity_threshold: float = 0.5,
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform pgvector cosine similarity search.

        Args:
            query_embedding: Query vector.
            filters: Search filters.
            limit: Maximum candidates.
            similarity_threshold: Minimum similarity score.

        Returns:
            List of (DocumentChunk, similarity_score) tuples.
        """
        connection = connections.get("default")
        where_conditions: list[str] = []
        params: list = []
        idx = 1

        vector_str = f"[{','.join(map(str, query_embedding))}]"
        where_conditions.append(f"(embedding <=> ${idx}) < ${idx + 1}")
        params.extend([vector_str, 1 - similarity_threshold])
        idx += 2

        if filters.chunk_types:
            where_conditions.append(f"chunk_type = ANY(${idx})")
            params.append([ct.value for ct in filters.chunk_types])
            idx += 1

        if filters.medicine_names:
            where_conditions.append(f"medicine_names && ${idx}")
            params.append(filters.medicine_names)
            idx += 1

        if filters.user_conditions:
            uc_values = [uc.value for uc in filters.user_conditions]
            where_conditions.append(f"NOT (contraindicated_conditions && ${idx})")
            params.append(uc_values)
            idx += 1
            where_conditions.append(f"(target_conditions = '[]'::jsonb OR target_conditions && ${idx})")
            params.append(uc_values)
            idx += 1

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"
        vector_param_idx = params.index(vector_str) + 1

        sql = f"""
        SELECT dc.*, (dc.embedding <=> ${vector_param_idx}) as distance
        FROM document_chunks dc
        WHERE {where_clause}
        ORDER BY distance ASC
        LIMIT ${idx}
        """  # noqa: S608
        params.append(limit)

        rows = await connection.execute_query_dict(sql, params)
        results = []
        for row in rows:
            distance = row.pop("distance")
            results.append((DocumentChunk(**row), 1 - distance))
        return results

    def calculate_keyword_score(
        self,
        query_keywords: list[str],
        chunk_keywords: list[str],
        chunk_content: str,
    ) -> float:
        """Calculate keyword matching score between query and chunk.

        Args:
            query_keywords: Keywords extracted from query.
            chunk_keywords: Keywords stored in chunk metadata.
            chunk_content: Full chunk content text.

        Returns:
            Score between 0.0 and 1.0.
        """
        if not query_keywords:
            return 0.0

        content_lower = chunk_content.lower()
        chunk_kw_lower = [k.lower() for k in chunk_keywords]
        matches = 0

        for keyword in query_keywords:
            kw_lower = keyword.lower()
            if kw_lower in chunk_kw_lower:
                matches += 2  # Exact keyword match weighted higher
            if kw_lower in content_lower:
                matches += 1

        max_possible = len(query_keywords) * 3
        return min(matches / max_possible, 1.0)

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from query text.

        Args:
            query: User query string.

        Returns:
            List of keyword strings.
        """
        words = re.findall(r"[가-힣a-zA-Z0-9]+", query)
        return [w for w in words if w.lower() not in _STOP_WORDS and len(w) > 1]

    async def _log_query(
        self,
        query: str,
        query_embedding: list[float],
        filters: SearchFilters,
        results: list[SearchResult],
        duration_ms: int,
    ) -> None:
        """Log search query for analytics.

        Args:
            query: Original query text.
            query_embedding: Query embedding vector.
            filters: Applied filters.
            results: Final search results.
            duration_ms: Search duration in milliseconds.
        """
        try:
            await SearchQuery(
                query_text=query,
                query_embedding=query_embedding,
                search_type="hybrid",
                filters_applied={
                    "user_conditions": [uc.value for uc in filters.user_conditions],
                    "medicine_names": filters.medicine_names,
                    "chunk_types": [ct.value for ct in filters.chunk_types],
                },
                results_count=len(results),
                top_chunk_ids=[r.chunk.id for r in results[:10]],
                search_duration_ms=duration_ms,
            ).save()
        except Exception as e:
            logger.warning("Failed to log search query: %s", e)
