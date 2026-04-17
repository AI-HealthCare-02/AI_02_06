"""Vector search service for RAG system."""

import logging
import re
import time

from tortoise import connections

from app.dtos.rag import SearchFilters, SearchResult
from app.models.vector_models import DocumentChunk, SearchQuery
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector-based similarity search with hybrid scoring."""

    def __init__(self, vector_weight: float = 0.7, keyword_weight: float = 0.3, metadata_weight: float = 0.1):
        """Initialize vector search service.

        Args:
            vector_weight: Weight for vector similarity score
            keyword_weight: Weight for keyword matching score
            metadata_weight: Weight for metadata matching score
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight

        # Normalize weights
        total_weight = vector_weight + keyword_weight + metadata_weight
        self.vector_weight /= total_weight
        self.keyword_weight /= total_weight
        self.metadata_weight /= total_weight

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
        user_profile_id: int | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector similarity and keyword matching.

        Args:
            query: Search query text
            filters: Search filters for metadata filtering
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity threshold
            user_profile_id: User profile ID for personalization

        Returns:
            List of search results sorted by relevance
        """
        start_time = time.time()

        if filters is None:
            filters = SearchFilters()

        try:
            # Step 1: Generate query embedding
            embedding_service = await get_embedding_service()
            query_embedding = await embedding_service.encode_single(query)

            # Step 2: Vector similarity search
            vector_results = await self._vector_similarity_search(
                query_embedding=query_embedding,
                filters=filters,
                limit=limit * 3,  # Get more candidates for reranking
                similarity_threshold=similarity_threshold,
            )

            if not vector_results:
                logger.info("No vector results found")
                return []

            # Step 3: Keyword matching
            keyword_scores = await self._calculate_keyword_scores(query, vector_results)

            # Step 4: Metadata scoring
            metadata_scores = await self._calculate_metadata_scores(filters, vector_results)

            # Step 5: Combine scores and rank
            final_results = self._combine_scores(vector_results, keyword_scores, metadata_scores)

            # Step 6: Apply final filtering and limit
            filtered_results = self._apply_final_filters(final_results, filters)
            final_results = filtered_results[:limit]

            # Step 7: Log search query
            search_duration = int((time.time() - start_time) * 1000)
            await self._log_search_query(
                query=query,
                query_embedding=query_embedding,
                filters=filters,
                results=final_results,
                search_duration=search_duration,
                user_profile_id=user_profile_id,
            )

            logger.info(f"Search completed: {len(final_results)} results in {search_duration}ms")
            return final_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def _vector_similarity_search(
        self, query_embedding: list[float], filters: SearchFilters, limit: int, similarity_threshold: float
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform vector similarity search using pgvector.

        Args:
            query_embedding: Query vector
            filters: Search filters
            limit: Maximum results
            similarity_threshold: Minimum similarity

        Returns:
            List of (chunk, similarity_score) tuples
        """
        connection = connections.get("default")

        # Build WHERE clause for filters
        where_conditions = []
        params = []
        param_index = 1

        # Add vector similarity condition
        vector_str = f"[{','.join(map(str, query_embedding))}]"
        where_conditions.append(f"(embedding <=> ${param_index}) < ${param_index + 1}")
        params.extend([vector_str, 1 - similarity_threshold])
        param_index += 2

        # Add metadata filters
        if filters.chunk_types:
            chunk_type_values = [ct.value for ct in filters.chunk_types]
            where_conditions.append(f"chunk_type = ANY(${param_index})")
            params.append(chunk_type_values)
            param_index += 1

        if filters.medicine_names:
            where_conditions.append(f"medicine_names && ${param_index}")
            params.append(filters.medicine_names)
            param_index += 1

        # User condition filtering (exclude contraindicated, include targeted)
        if filters.user_conditions:
            user_condition_values = [uc.value for uc in filters.user_conditions]

            # Exclude contraindicated
            where_conditions.append(f"NOT (contraindicated_conditions && ${param_index})")
            params.append(user_condition_values)
            param_index += 1

            # Include targeted or general (empty target_conditions)
            where_conditions.append(f"(target_conditions = '[]'::jsonb OR target_conditions && ${param_index})")
            params.append(user_condition_values)
            param_index += 1

        # Build final query
        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        sql = f"""
        SELECT
            dc.*,
            (dc.embedding <=> ${params.index(vector_str) + 1}) as distance
        FROM document_chunks dc
        WHERE {where_clause}
        ORDER BY distance ASC
        LIMIT ${param_index}
        """
        params.append(limit)

        # Execute query
        results = await connection.execute_query_dict(sql, params)

        # Convert to DocumentChunk objects with similarity scores
        vector_results = []
        for row in results:
            distance = row.pop("distance")
            similarity = 1 - distance  # Convert distance to similarity

            # Create DocumentChunk instance
            chunk = DocumentChunk(**row)
            vector_results.append((chunk, similarity))

        return vector_results

    async def _calculate_keyword_scores(
        self, query: str, vector_results: list[tuple[DocumentChunk, float]]
    ) -> list[float]:
        """Calculate keyword matching scores for search results.

        Args:
            query: Original search query
            vector_results: Results from vector search

        Returns:
            List of keyword scores (0-1)
        """
        # Extract keywords from query
        query_keywords = self._extract_query_keywords(query)

        if not query_keywords:
            return [0.0] * len(vector_results)

        keyword_scores = []
        for chunk, _ in vector_results:
            # Get chunk keywords and content
            chunk_keywords = chunk.keywords or []
            chunk_content = chunk.content.lower()

            # Calculate keyword matches
            keyword_matches = 0
            content_matches = 0

            for keyword in query_keywords:
                keyword_lower = keyword.lower()

                # Check exact keyword match
                if keyword_lower in [ck.lower() for ck in chunk_keywords]:
                    keyword_matches += 2  # Higher weight for exact keyword match

                # Check content match
                if keyword_lower in chunk_content:
                    content_matches += 1

            # Calculate final keyword score
            total_matches = keyword_matches + content_matches
            max_possible = len(query_keywords) * 3  # Max if all keywords match both ways

            keyword_score = total_matches / max_possible if max_possible > 0 else 0.0
            keyword_scores.append(min(keyword_score, 1.0))

        return keyword_scores

    def _extract_query_keywords(self, query: str) -> list[str]:
        """Extract keywords from search query.

        Args:
            query: Search query

        Returns:
            List of extracted keywords
        """
        stop_words = {"은", "는", "이", "가", "을", "를", "의", "에", "에서", "로", "으로", "와", "과", "하고"}
        words = re.findall(r"[가-힣a-zA-Z0-9]+", query)
        return [word for word in words if word.lower() not in stop_words and len(word) > 1]

    async def _calculate_metadata_scores(
        self, filters: SearchFilters, vector_results: list[tuple[DocumentChunk, float]]
    ) -> list[float]:
        """Calculate metadata matching scores.

        Args:
            filters: Search filters
            vector_results: Results from vector search

        Returns:
            List of metadata scores (0-1)
        """
        metadata_scores = []

        for chunk, _ in vector_results:
            score = 0.0
            total_criteria = 0

            # User condition matching
            if filters.user_conditions:
                total_criteria += 1
                chunk_conditions = chunk.target_conditions or []

                if not chunk_conditions:  # General content
                    score += 0.5
                else:
                    # Check for matching conditions
                    matches = len(set(filters.user_conditions) & set(chunk_conditions))
                    if matches > 0:
                        score += 1.0

            # Medicine name matching
            if filters.medicine_names:
                total_criteria += 1
                chunk_medicines = chunk.medicine_names or []

                if chunk_medicines:
                    matches = len(set(filters.medicine_names) & set(chunk_medicines))
                    if matches > 0:
                        score += 1.0

            # Chunk type matching
            if filters.chunk_types:
                total_criteria += 1
                if chunk.chunk_type in filters.chunk_types:
                    score += 1.0

            # Calculate final metadata score
            metadata_score = score / total_criteria if total_criteria > 0 else 0.5
            metadata_scores.append(metadata_score)

        return metadata_scores

    def _combine_scores(
        self,
        vector_results: list[tuple[DocumentChunk, float]],
        keyword_scores: list[float],
        metadata_scores: list[float],
    ) -> list[SearchResult]:
        """Combine all scores into final search results.

        Args:
            vector_results: Vector search results
            keyword_scores: Keyword matching scores
            metadata_scores: Metadata matching scores

        Returns:
            List of SearchResult objects with combined scores
        """
        results = []

        for i, (chunk, vector_score) in enumerate(vector_results):
            keyword_score = keyword_scores[i] if i < len(keyword_scores) else 0.0
            metadata_score = metadata_scores[i] if i < len(metadata_scores) else 0.0

            # Calculate weighted final score
            final_score = (
                self.vector_weight * vector_score
                + self.keyword_weight * keyword_score
                + self.metadata_weight * metadata_score
            )

            results.append(
                SearchResult(
                    chunk=chunk,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    metadata_score=metadata_score,
                    final_score=final_score,
                )
            )

        # Sort by final score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)

        return results

    def _apply_final_filters(self, results: list[SearchResult], filters: SearchFilters) -> list[SearchResult]:  # noqa: ARG002
        """Apply final filtering to search results.

        Args:
            results: Search results
            filters: Search filters

        Returns:
            Filtered search results
        """
        # For now, just return as-is since filtering was done in SQL
        # Additional post-processing filters can be added here
        return results

    async def _log_search_query(
        self,
        query: str,
        query_embedding: list[float],
        filters: SearchFilters,
        results: list[SearchResult],
        search_duration: int,
        user_profile_id: int | None,
    ) -> None:
        """Log search query for analytics.

        Args:
            query: Search query
            query_embedding: Query embedding vector
            filters: Applied filters
            results: Search results
            search_duration: Search duration in milliseconds
            user_profile_id: User profile ID
        """
        try:
            # Prepare filters for JSON storage
            filters_dict = {
                "user_conditions": [uc.value for uc in filters.user_conditions],
                "medicine_names": filters.medicine_names,
                "chunk_types": [ct.value for ct in filters.chunk_types],
                "date_range": filters.date_range,
            }

            # Create search query record
            search_query = SearchQuery(
                query_text=query,
                query_embedding=query_embedding,
                search_type="hybrid_search",
                filters_applied=filters_dict,
                results_count=len(results),
                top_chunk_ids=[result.chunk.id for result in results[:10]],
                search_duration_ms=search_duration,
                user_profile_id=user_profile_id,
                user_conditions=[uc.value for uc in filters.user_conditions],
            )

            await search_query.save()

        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")


# Global search service instance
_search_service: VectorSearchService | None = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create global vector search service instance.

    Returns:
        Vector search service instance
    """
    global _search_service

    if _search_service is None:
        _search_service = VectorSearchService()

    return _search_service
