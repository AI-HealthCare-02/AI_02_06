"""RAG Pipeline orchestrator.

Combines IntentClassifier, EmbeddingProvider, Retriever, and ToolRouter
to process user queries end-to-end.
"""

import logging
import time

from app.dtos.rag import RAGResponse, SearchFilters, SearchResult
from app.services.rag.intent.classifier import IntentClassifier
from app.services.rag.intent.intents import IntentType
from app.services.rag.protocols import EmbeddingProvider, Retriever

logger = logging.getLogger(__name__)

# Intents that require RAG retrieval
_RAG_INTENTS: frozenset[IntentType] = frozenset({
    IntentType.MEDICATION_INFO,
    IntentType.DRUG_INTERACTION,
    IntentType.SUPPLEMENT_INFO,
})

# Intents handled directly without retrieval or tools
_DIRECT_INTENTS: frozenset[IntentType] = frozenset({
    IntentType.GENERAL_CHAT,
    IntentType.OUT_OF_SCOPE,
})

_OUT_OF_SCOPE_REPLY = (
    "죄송합니다. 저는 복약 및 건강 관련 질문만 도와드릴 수 있어요. 약 복용법, 부작용, 영양제 등에 대해 질문해 주세요."
)


class RAGPipeline:
    """Orchestrates intent classification, retrieval, and response generation.

    Dependencies are injected to allow swapping components independently.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        retriever: Retriever,
        intent_classifier: IntentClassifier,
        tool_router: object,
        rag_generator: object,
    ) -> None:
        """Initialize RAG pipeline with all required components.

        Args:
            embedding_provider: Embedding model for query encoding.
            retriever: Search strategy for document retrieval.
            intent_classifier: Classifier for user intent detection.
            tool_router: Router for tool-based intent handling.
            rag_generator: LLM generator for response creation.
        """
        self.embedding_provider = embedding_provider
        self.retriever = retriever
        self.intent_classifier = intent_classifier
        self.tool_router = tool_router
        self.rag_generator = rag_generator

    async def ask(
        self,
        question: str,
        history: list[dict[str, str]],
        system_prompt: str | None = None,
        user_profile_id: int | None = None,
        max_sources: int = 5,
    ) -> RAGResponse:
        """Process a user question through the full RAG pipeline.

        Args:
            question: User's question text.
            history: Previous conversation messages.
            system_prompt: Optional custom system prompt for LLM.
            user_profile_id: User profile ID for downstream tool handlers.
            max_sources: Maximum number of medicine sources to retrieve.

        Returns:
            RAGResponse with answer, sources, and metadata.
        """
        start_time = time.time()

        # Step 1: Classify intent
        intent = self.intent_classifier.classify(question)
        logger.info("Intent classified as: %s", intent)

        # Step 2: Handle out-of-scope directly
        if intent == IntentType.OUT_OF_SCOPE:
            return RAGResponse(
                answer=_OUT_OF_SCOPE_REPLY,
                sources=[],
                confidence_score=1.0,
                search_results_count=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Step 3: Handle general chat directly
        if intent == IntentType.GENERAL_CHAT:
            messages = [*history, {"role": "user", "content": question}]
            answer = await self.rag_generator.generate_chat_response(messages, system_prompt=system_prompt)
            return RAGResponse(
                answer=answer,
                sources=[],
                confidence_score=1.0,
                search_results_count=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Step 4: RAG retrieval for knowledge-based intents
        if intent in _RAG_INTENTS:
            query_embedding = await self.embedding_provider.encode_single(question)
            filters = SearchFilters()

            search_results = await self.retriever.retrieve(
                query=question,
                query_embedding=query_embedding,
                filters=filters,
                limit=max_sources,
            )

            context = self._build_context(search_results)
            messages = [*history, {"role": "user", "content": question}]
            prompt = system_prompt or self._default_system_prompt(context)

            answer = await self.rag_generator.generate_chat_response(messages, system_prompt=prompt)
            confidence = self._calculate_confidence(search_results)
            sources = self._build_sources(search_results)

            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=confidence,
                search_results_count=len(search_results),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Step 5: Tool-based intents (MY_SCHEDULE, NEARBY_HOSPITAL, WEATHER, etc.)
        answer = await self.tool_router.execute(
            intent=intent,
            query=question,
            context={"history": history, "user_profile_id": user_profile_id},
        )
        return RAGResponse(
            answer=answer,
            sources=[],
            confidence_score=1.0,
            search_results_count=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    def _build_context(self, search_results: list[SearchResult]) -> str:
        """Build context string from MedicineInfo search results.

        Args:
            search_results: Ranked MedicineInfo matches.

        Returns:
            Formatted context string for LLM prompt.
        """
        if not search_results:
            return ""
        parts: list[str] = []
        for r in search_results:
            m = r.medicine
            drugs = ", ".join(m.contraindicated_drugs or []) or "해당 없음"
            foods = ", ".join(m.contraindicated_foods or []) or "해당 없음"
            parts.append(
                f"[{m.name}]\n"
                f"주성분: {m.ingredient}\n"
                f"용도: {m.usage}\n"
                f"주의사항: {m.disclaimer}\n"
                f"병용 금기 약물: {drugs}\n"
                f"병용 금기 음식: {foods}"
            )
        return "\n\n".join(parts)

    def _default_system_prompt(self, context: str) -> str:
        """Build default system prompt with retrieved context.

        Args:
            context: Retrieved document context.

        Returns:
            System prompt string.
        """
        return (
            "당신은 친절하고 전문적인 약사 AI 'Dayak'입니다.\n"
            "아래 [Context]의 정보를 바탕으로 사용자의 질문에 답변해주세요.\n"
            "[Context]에 관련 정보가 없으면 일반 의학 지식으로 답변하되, "
            "반드시 전문가 상담을 권유하세요.\n\n"
            f"[Context]\n{context}"
        )

    def _calculate_confidence(self, search_results: list[SearchResult]) -> float:
        """Calculate confidence score from MedicineInfo matches.

        Args:
            search_results: Ranked MedicineInfo matches.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        if not search_results:
            return 0.0
        avg = sum(r.final_score for r in search_results) / len(search_results)
        diversity = min(len({r.medicine.usage for r in search_results}) * 0.1, 0.3)
        return min(avg + diversity, 1.0)

    def _build_sources(self, search_results: list[SearchResult]) -> list[dict]:
        """Build source payload returned to the API client.

        Args:
            search_results: Ranked MedicineInfo matches.

        Returns:
            List of lightweight source dicts.
        """
        return [
            {
                "name": r.medicine.name,
                "usage": r.medicine.usage,
                "ingredient": r.medicine.ingredient,
                "relevance_score": round(r.final_score, 3),
            }
            for r in search_results
        ]
