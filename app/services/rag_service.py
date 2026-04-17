"""RAG (Retrieval-Augmented Generation) service for pharmaceutical Q&A."""

from dataclasses import dataclass
from datetime import UTC
import logging
from typing import Any

from app.models.vector_models import DocumentChunk, DocumentType, PharmaceuticalDocument, UserCondition
from app.services.chunking_service import get_document_chunker
from app.services.embedding_service import get_embedding_service
from app.services.vector_search_service import SearchFilters, get_vector_search_service
from app.utils.rag import RAGGenerator

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from RAG system."""

    answer: str
    sources: list[dict[str, Any]]
    confidence_score: float
    search_results_count: int
    processing_time_ms: int


class RAGService:
    """Main service for RAG-based pharmaceutical question answering."""

    def __init__(self):
        """Initialize RAG service."""
        self.rag_generator = RAGGenerator()

    async def ask_question(
        self,
        question: str,
        user_conditions: list[UserCondition] | None = None,
        user_profile_id: int | None = None,
        max_sources: int = 5,
    ) -> RAGResponse:
        """Answer a pharmaceutical question using RAG.

        Args:
            question: User's question
            user_conditions: User's health conditions for personalization
            user_profile_id: User profile ID for logging
            max_sources: Maximum number of source chunks to use

        Returns:
            RAG response with answer and sources
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"Processing question: {question[:100]}...")

            # Step 1: Prepare search filters
            filters = SearchFilters(user_conditions=user_conditions or [])

            # Step 2: Perform hybrid search
            search_service = get_vector_search_service()
            search_results = await search_service.search(
                query=question,
                filters=filters,
                limit=max_sources * 2,  # Get more for better selection
                user_profile_id=user_profile_id,
            )

            if not search_results:
                no_result_msg = (
                    "죄송합니다. 관련된 정보를 찾을 수 없습니다. "
                    "더 구체적인 질문을 해주시거나 의료진과 상담하시기 바랍니다."
                )
                return RAGResponse(
                    answer=no_result_msg,
                    sources=[],
                    confidence_score=0.0,
                    search_results_count=0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            # Step 3: Select best sources
            selected_sources = self._select_best_sources(search_results, max_sources)

            # Step 4: Generate answer using RAG
            context_chunks = [result.chunk for result in selected_sources]
            answer = await self.rag_generator.generate_guide(
                question=question, context_chunks=context_chunks, user_conditions=user_conditions or []
            )

            # Step 5: Calculate confidence score
            confidence_score = self._calculate_confidence_score(selected_sources)

            # Step 6: Prepare source information
            sources = self._prepare_source_info(selected_sources)

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(f"Question answered in {processing_time}ms with {len(sources)} sources")

            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=confidence_score,
                search_results_count=len(search_results),
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"RAG question answering failed: {e}")
            processing_time = int((time.time() - start_time) * 1000)

            return RAGResponse(
                answer="죄송합니다. 시스템 오류로 인해 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
                sources=[],
                confidence_score=0.0,
                search_results_count=0,
                processing_time_ms=processing_time,
            )

    async def index_document(
        self,
        title: str,
        content: str,
        document_type: DocumentType,
        medicine_names: list[str] | None = None,
        target_conditions: list[UserCondition] | None = None,
        source_url: str | None = None,
    ) -> PharmaceuticalDocument:
        """Index a new pharmaceutical document for RAG.

        Args:
            title: Document title
            content: Document content
            document_type: Type of document
            medicine_names: List of medicine names in document
            target_conditions: Target user conditions
            source_url: Source URL if available

        Returns:
            Created document instance
        """
        try:
            logger.info(f"Indexing document: {title}")

            # Step 1: Create document record
            embedding_service = await get_embedding_service()
            content_hash = embedding_service.generate_content_hash(content)

            # Check for duplicates
            existing_doc = await PharmaceuticalDocument.filter(content_hash=content_hash).first()

            if existing_doc:
                logger.info(f"Document already exists: {existing_doc.id}")
                return existing_doc

            # Step 2: Generate document-level embedding
            document_embedding = await embedding_service.encode_single(f"{title}\n{content}")

            # Step 3: Create document
            document = await PharmaceuticalDocument.create(
                title=title,
                document_type=document_type,
                source_url=source_url,
                content=content,
                content_hash=content_hash,
                medicine_names=medicine_names or [],
                target_conditions=[uc.value for uc in (target_conditions or [])],
                document_embedding=document_embedding,
            )

            # Step 4: Chunk document
            chunker = get_document_chunker()
            chunks = chunker.chunk_document(content, title)

            # Step 5: Generate embeddings for chunks and save
            chunk_texts = [chunk.content for chunk in chunks]
            chunk_embeddings = await embedding_service.encode_batch(chunk_texts)

            for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings, strict=True)):
                chunk_hash = embedding_service.generate_content_hash(chunk.content)

                await DocumentChunk.create(
                    document=document,
                    chunk_index=i,
                    chunk_type=chunk.chunk_type,
                    content=chunk.content,
                    content_hash=chunk_hash,
                    section_title=chunk.section_title,
                    word_count=chunk.word_count,
                    char_count=chunk.char_count,
                    keywords=chunk.keywords,
                    medicine_names=medicine_names or [],
                    target_conditions=[uc.value for uc in (target_conditions or [])],
                    embedding=embedding,
                    embedding_normalized=True,  # Our service normalizes embeddings
                )

            logger.info(f"Document indexed successfully: {document.id} with {len(chunks)} chunks")
            return document

        except Exception as e:
            logger.error(f"Document indexing failed: {e}")
            raise

    def _select_best_sources(self, search_results: list, max_sources: int) -> list:
        """Select the best sources from search results.

        Args:
            search_results: List of search results
            max_sources: Maximum number of sources to select

        Returns:
            Selected search results
        """
        # Sort by final score and select top results
        sorted_results = sorted(search_results, key=lambda x: x.final_score, reverse=True)

        # Ensure diversity in chunk types
        selected = []
        chunk_types_seen = set()

        for result in sorted_results:
            if len(selected) >= max_sources:
                break

            # Prefer diverse chunk types for comprehensive answers
            if result.chunk.chunk_type not in chunk_types_seen or len(selected) < max_sources // 2:
                selected.append(result)
                chunk_types_seen.add(result.chunk.chunk_type)

        # Fill remaining slots with highest scoring results
        for result in sorted_results:
            if len(selected) >= max_sources:
                break
            if result not in selected:
                selected.append(result)

        return selected

    def _calculate_confidence_score(self, selected_sources: list) -> float:
        """Calculate confidence score based on source quality.

        Args:
            selected_sources: Selected search results

        Returns:
            Confidence score between 0 and 1
        """
        if not selected_sources:
            return 0.0

        # Average of final scores
        avg_score = sum(result.final_score for result in selected_sources) / len(selected_sources)

        # Boost confidence if we have diverse chunk types
        chunk_types = {result.chunk.chunk_type for result in selected_sources}
        diversity_bonus = min(len(chunk_types) * 0.1, 0.3)

        # Boost confidence if we have high vector similarity
        avg_vector_score = sum(result.vector_score for result in selected_sources) / len(selected_sources)
        vector_bonus = max(0, (avg_vector_score - 0.7) * 0.5)

        final_confidence = min(avg_score + diversity_bonus + vector_bonus, 1.0)
        return final_confidence

    def _prepare_source_info(self, selected_sources: list) -> list[dict[str, Any]]:
        """Prepare source information for response.

        Args:
            selected_sources: Selected search results

        Returns:
            List of source information dictionaries
        """
        sources = []

        for result in selected_sources:
            chunk = result.chunk

            source_info = {
                "chunk_id": chunk.id,
                "document_title": chunk.document.title if hasattr(chunk, "document") else "Unknown",
                "section_title": chunk.section_title,
                "chunk_type": chunk.chunk_type.value,
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "relevance_score": round(result.final_score, 3),
                "vector_score": round(result.vector_score, 3),
                "keyword_score": round(result.keyword_score, 3),
                "metadata_score": round(result.metadata_score, 3),
            }

            sources.append(source_info)

        return sources

    async def get_search_analytics(self, days: int = 7) -> dict[str, Any]:
        """Get search analytics for the past N days.

        Args:
            days: Number of days to analyze

        Returns:
            Analytics data
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now(tz=UTC) - timedelta(days=days)

        # Get search queries from the past N days
        from app.models.vector_models import SearchQuery

        recent_queries = await SearchQuery.filter(created_at__gte=cutoff_date).all()

        if not recent_queries:
            return {
                "total_queries": 0,
                "avg_response_time_ms": 0,
                "avg_results_count": 0,
                "popular_search_types": {},
                "common_filters": {},
            }

        # Calculate analytics
        total_queries = len(recent_queries)
        avg_response_time = sum(q.search_duration_ms for q in recent_queries) / total_queries
        avg_results_count = sum(q.results_count for q in recent_queries) / total_queries

        # Popular search types
        search_types = {}
        for query in recent_queries:
            search_type = query.search_type
            search_types[search_type] = search_types.get(search_type, 0) + 1

        # Common filters
        filter_usage = {}
        for query in recent_queries:
            filters = query.filters_applied or {}
            for filter_type, filter_value in filters.items():
                if filter_value:  # Only count non-empty filters
                    filter_usage[filter_type] = filter_usage.get(filter_type, 0) + 1

        return {
            "total_queries": total_queries,
            "avg_response_time_ms": round(avg_response_time, 2),
            "avg_results_count": round(avg_results_count, 2),
            "popular_search_types": search_types,
            "common_filters": filter_usage,
        }


# Global RAG service instance
_rag_service: RAGService | None = None


async def get_rag_service() -> RAGService:
    """Get or create global RAG service instance.

    Returns:
        RAG service instance
    """
    global _rag_service

    if _rag_service is None:
        _rag_service = RAGService()

    return _rag_service
