"""RAG Pipeline orchestrator.

Combines IntentClassifier, EmbeddingProvider, Retriever, and ToolRouter
to process user queries end-to-end.
"""

from collections.abc import Awaitable, Callable
import logging
import time
from uuid import UUID

from app.dtos.rag import (
    RAGResponse,
    RetrievalMetadata,
    RewriteStatus,
    SearchFilters,
    SearchResult,
    TokenUsage,
)
from app.repositories.profile_repository import ProfileRepository
from app.services.rag.intent.classifier import IntentClassifier
from app.services.rag.intent.intents import IntentType
from app.services.rag.protocols import EmbeddingProvider, Retriever

# Number of trailing turns (user/assistant alternating) retained verbatim
# for the answer LLM. The rewrite stage already consumed full history;
# keeping only recent turns here preserves conversational tone while
# cutting prompt tokens.
_ANSWER_HISTORY_TURNS: int = 3

logger = logging.getLogger(__name__)

# Intents that require RAG retrieval.
_RAG_INTENTS: frozenset[IntentType] = frozenset({
    IntentType.MEDICATION_INFO,
    IntentType.DRUG_INTERACTION,
    IntentType.SUPPLEMENT_INFO,
})

# Intents handled directly without retrieval or tools.
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
        profile_repository: ProfileRepository | None = None,
    ) -> None:
        """Initialize RAG pipeline with all required components.

        Args:
            embedding_provider: Embedding model for query encoding.
            retriever: Search strategy for document retrieval.
            intent_classifier: Classifier for user intent detection.
            tool_router: Router for tool-based intent handling.
            rag_generator: LLM generator for response creation.
            profile_repository: Optional profile repository used to fetch
                the active profile's health_survey (allergies, chronic
                conditions) for prompt augmentation. When omitted, the
                medical-context block is simply skipped.
        """
        self.embedding_provider = embedding_provider
        self.retriever = retriever
        self.intent_classifier = intent_classifier
        self.tool_router = tool_router
        self.rag_generator = rag_generator
        self.profile_repository = profile_repository

        # Intent -> handler dispatch table (replaces if/elif chain).
        self._handlers: dict[IntentType, Callable[..., Awaitable[RAGResponse]]] = {
            IntentType.OUT_OF_SCOPE: self._handle_out_of_scope,
            IntentType.GENERAL_CHAT: self._handle_general_chat,
            IntentType.MEDICATION_INFO: self._handle_rag_retrieval,
            IntentType.DRUG_INTERACTION: self._handle_rag_retrieval,
            IntentType.SUPPLEMENT_INFO: self._handle_rag_retrieval,
        }

    async def ask(
        self,
        question: str,
        history: list[dict[str, str]],
        system_prompt: str | None = None,
        user_profile_id: UUID | None = None,
        max_sources: int = 5,
        history_metadata: list[dict] | None = None,  # noqa: ARG002  reserved for Compact phase (session summary injection)
    ) -> RAGResponse:
        """Process a user question through the full RAG pipeline.

        Args:
            question: User's question text.
            history: Previous conversation messages.
            system_prompt: Optional custom system prompt for LLM.
            user_profile_id: Active profile UUID for medical-context lookup
                and downstream tool handlers.
            max_sources: Maximum number of medicine sources to retrieve.
            history_metadata: Per-turn metadata aligned with ``history``,
                reserved for the session-summary/Compact phase.

        Returns:
            RAGResponse with answer, sources, and metadata.
        """
        start_time = time.time()

        intent = self.intent_classifier.classify(question)
        logger.info("[RAG] intent=%s history=%dturns", intent.value, len(history))

        handler = self._handlers.get(intent, self._handle_tool_execution)

        return await handler(
            question=question,
            history=history,
            intent=intent,
            system_prompt=system_prompt,
            max_sources=max_sources,
            user_profile_id=user_profile_id,
            start_time=start_time,
        )

    # -------------------------------------------------------------------------
    # Route handlers
    # -------------------------------------------------------------------------

    async def _handle_out_of_scope(self, intent: IntentType, start_time: float, **_kwargs) -> RAGResponse:
        """Handle out-of-scope questions directly."""
        logger.info("[RAG] path=out_of_scope")
        return self._create_response(
            answer=_OUT_OF_SCOPE_REPLY,
            intent=intent,
            start_time=start_time,
        )

    async def _handle_general_chat(
        self,
        question: str,
        history: list[dict[str, str]],
        intent: IntentType,
        system_prompt: str | None,
        start_time: float,
        **_kwargs,
    ) -> RAGResponse:
        """Handle general chat without retrieval."""
        messages = [*history, {"role": "user", "content": question}]
        logger.info("[RAG] path=general_chat llm_msgs=%d", len(messages))

        completion = await self.rag_generator.generate_chat_response(messages, system_prompt=system_prompt)

        return self._create_response(
            answer=completion.answer,
            intent=intent,
            start_time=start_time,
            token_usage=completion.token_usage,
        )

    async def _handle_rag_retrieval(
        self,
        question: str,
        history: list[dict[str, str]],
        intent: IntentType,
        system_prompt: str | None,
        max_sources: int,
        user_profile_id: UUID | None,
        start_time: float,
        **_kwargs,
    ) -> RAGResponse:
        """Handle knowledge-grounded intents via retrieve + LLM."""
        logger.info("[RAG] path=retrieve+llm")

        # Step 1: LLM-based query rewriting with full history.
        logger.info("[RAG] rewrite: starting (history=%dturns)", len(history))
        rewrite = await self.rag_generator.rewrite_query(history=history, current_query=question)

        unresolvable = rewrite.status == RewriteStatus.UNRESOLVABLE
        effective_query = rewrite.query

        # Step 2: Skip retrieval when the query is unresolvable; the answer
        # LLM is instructed to ask a clarifying question instead.
        search_results: list[SearchResult] = []
        if not unresolvable:
            search_results = await self._fetch_search_results(effective_query, max_sources)

        # Step 3: Build the system prompt. Clarify path short-circuits the
        # augmented prompt entirely.
        if unresolvable:
            prompt = self._clarify_system_prompt()
            user_content = effective_query
        else:
            prompt = system_prompt or self._build_system_prompt()
            user_content = await self._build_augmented_user_prompt(
                effective_query=effective_query,
                search_results=search_results,
                user_profile_id=user_profile_id,
            )

        # Step 4: Keep only the last few turns for the answer LLM. Rewrite
        # already consumed full history; repeating it wastes tokens.
        tail_history = history[-_ANSWER_HISTORY_TURNS:] if _ANSWER_HISTORY_TURNS > 0 else []
        messages = [*tail_history, {"role": "user", "content": user_content}]

        logger.info(
            "[RAG] llm msgs=%d history_turns=%d user_content_chars=%d%s",
            len(messages),
            len(tail_history),
            len(user_content),
            " prompt=clarify" if unresolvable else "",
        )
        completion = await self.rag_generator.generate_chat_response(messages, system_prompt=prompt)

        query_keywords = (
            self.retriever.extract_keywords(effective_query) if hasattr(self.retriever, "extract_keywords") else []
        )

        return self._create_response(
            answer=completion.answer,
            intent=intent,
            start_time=start_time,
            sources=self._build_sources(search_results),
            confidence_score=self._calculate_confidence(search_results),
            search_results_count=len(search_results),
            query_keywords=query_keywords,
            retrieval=self._build_retrieval_metadata(search_results),
            token_usage=completion.token_usage,
        )

    async def _handle_tool_execution(
        self,
        question: str,
        history: list[dict[str, str]],
        intent: IntentType,
        user_profile_id: UUID | None,
        start_time: float,
        **_kwargs,
    ) -> RAGResponse:
        """Handle tool-based intents (nearby hospital, weather, etc.)."""
        logger.info("[RAG] path=tool intent=%s", intent.value)
        answer = await self.tool_router.execute(
            intent=intent,
            query=question,
            context={"history": history, "user_profile_id": user_profile_id},
        )
        return self._create_response(
            answer=answer,
            intent=intent,
            start_time=start_time,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    async def _fetch_search_results(self, effective_query: str, max_sources: int) -> list[SearchResult]:
        """Embed the query and retrieve matching medicine documents."""
        query_embedding = await self.embedding_provider.encode_single(effective_query)
        results = await self.retriever.retrieve(
            query=effective_query,
            query_embedding=query_embedding,
            filters=SearchFilters(),
            limit=max_sources,
        )
        if results:
            summary = ", ".join(
                f"{r.medicine.medicine_name}({r.final_score:.2f}, {len(r.matched_chunks)}chunks)" for r in results
            )
            logger.info("[RAG] retrieved=%d: %s", len(results), summary)
        else:
            logger.info("[RAG] retrieved=0 (no matches above threshold)")
        return results

    async def _fetch_user_medical_context(self, user_profile_id: UUID | None) -> str | None:
        """Fetch the active profile's medical context string for prompting.

        Renders every non-empty field of ``profile.health_survey`` (JSONB)
        as a bullet list so the answer LLM sees the full user context
        (age, gender, allergies, chronic conditions, and any future
        fields added to the survey). Returns ``None`` when no repository
        is wired, no profile id is supplied, the profile is missing, or
        the survey carries no usable fields — callers then omit the
        medical-context block from the prompt entirely.
        """
        if self.profile_repository is None or user_profile_id is None:
            return None

        profile = await self.profile_repository.get_by_id(user_profile_id)
        if profile is None or not profile.health_survey:
            return None

        lines = [
            f"- {self._format_survey_entry(key, value)}"
            for key, value in profile.health_survey.items()
            if self._format_survey_entry(key, value) is not None
        ]
        return "\n".join(lines) if lines else None

    @staticmethod
    def _format_survey_entry(key: str, value: object) -> str | None:
        """Render a single ``health_survey`` entry as ``"<key>: <value>"``.

        Drops empty/placeholder values (``None``, empty containers, or
        the sentinel string ``"None"``) so we never inject meaningless
        lines like ``알레르기: None`` into the LLM prompt.
        """
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned or cleaned == "None":
                return None
            return f"{key}: {cleaned}"
        if isinstance(value, (list, tuple, set)):
            items = [str(item).strip() for item in value if item not in (None, "", "None")]
            if not items:
                return None
            return f"{key}: {', '.join(items)}"
        if isinstance(value, dict):
            if not value:
                return None
            inner = ", ".join(f"{k}={v}" for k, v in value.items() if v not in (None, "", "None"))
            return f"{key}: {inner}" if inner else None
        return f"{key}: {value}"

    async def _build_augmented_user_prompt(
        self,
        effective_query: str,
        search_results: list[SearchResult],
        user_profile_id: UUID | None,
    ) -> str:
        """Assemble the markdown-structured user prompt.

        Medical context is included only when we actually have profile
        data; otherwise the section is dropped so we never invent
        allergy/condition facts.
        """
        sections: list[str] = []

        medical_context = await self._fetch_user_medical_context(user_profile_id)
        if medical_context:
            sections.append(f"### 사용자 기저 정보\n{medical_context}")

        retrieved_docs = self._build_context(search_results)
        if retrieved_docs:
            sections.append(f"### DB 검색 참고 문서\n{retrieved_docs}")

        sections.append(f"### 사용자 질문\n**{effective_query}**")
        return "\n\n".join(sections)

    def _build_system_prompt(self) -> str:
        """Markdown-structured system rules for the answer LLM."""
        return (
            "# Role\n"
            "당신은 친절하고 전문적인 약사 AI 'Dayak'입니다.\n\n"
            "# Rule\n"
            "- 반드시 하단에 제공된 **[참고 문서]** 및 사용자의 **[기저 정보]**를 바탕으로만 답변하세요.\n"
            "- 제공된 정보로 알 수 없는 내용은 절대 지어내지 말고, 의사/약사와 상담할 것을 권유하세요.\n"
            "- 위험한 부작용이나 알레르기 충돌이 예상되면 가장 먼저 **경고**하세요.\n\n"
            "# Task\n"
            "사용자의 질문에 대해 약학적 근거를 바탕으로 안전한 복약 가이드를 제공하세요.\n\n"
            "# Output Format\n"
            "- 결론을 먼저 말하세요.\n"
            "- 이유는 불릿 포인트(`-`)를 사용하여 간결하게 정리하세요."
        )

    def _create_response(
        self,
        answer: str,
        intent: IntentType,
        start_time: float,
        sources: list[dict] | None = None,
        confidence_score: float = 1.0,
        search_results_count: int = 0,
        query_keywords: list[str] | None = None,
        retrieval: RetrievalMetadata | None = None,
        token_usage: TokenUsage | None = None,
    ) -> RAGResponse:
        """Factory that keeps RAGResponse construction consistent across paths."""
        return RAGResponse(
            answer=answer,
            sources=sources or [],
            confidence_score=confidence_score,
            search_results_count=search_results_count,
            processing_time_ms=int((time.time() - start_time) * 1000),
            intent=intent.value,
            query_keywords=query_keywords or [],
            retrieval=retrieval or RetrievalMetadata(),
            token_usage=token_usage,
        )

    def _build_context(self, search_results: list[SearchResult]) -> str:
        """Build context string from MedicineInfo search results.

        Args:
            search_results: Ranked MedicineInfo matches.

        Returns:
            Formatted context string for the LLM prompt.
        """
        if not search_results:
            return ""
        parts: list[str] = []
        for r in search_results:
            m = r.medicine
            header_lines = [f"[{m.medicine_name}]"]
            if m.category:
                header_lines.append(f"분류: {m.category}")
            if m.entp_name:
                header_lines.append(f"제조사: {m.entp_name}")
            header = "\n".join(header_lines)

            # Chunk-based body: render each matched chunk with its section tag.
            # Section code (e.g. "efficacy") is kept as-is for the LLM since
            # it maps 1:1 to the public API ARTICLE structure the team uses.
            chunk_lines = [f"  - [{cm.chunk.section}] {cm.chunk.content}" for cm in r.matched_chunks]
            body = "\n".join(chunk_lines) if chunk_lines else "  (매칭된 청크 없음)"
            parts.append(f"{header}\n{body}")
        return "\n\n".join(parts)

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
        # Diversity bonus now keyed by medicine_info.category (main schema);
        # the old MedicineInfo.usage field no longer exists.
        categories = {r.medicine.category for r in search_results if r.medicine.category}
        diversity = min(len(categories) * 0.1, 0.3)
        return min(avg + diversity, 1.0)

    def _clarify_system_prompt(self) -> str:
        """System prompt used when the query is ambiguous and no history hint exists.

        Instructs the LLM to ask the user which medicine they mean
        instead of guessing. Keeps the friendly Dayak persona.
        """
        return (
            "당신은 친절하고 전문적인 약사 AI 'Dayak'입니다.\n"
            "사용자의 질문이 어떤 약에 대한 것인지 불분명하고, 대화 이력에서도 특정 약을 "
            "유추할 수 없습니다. 어느 약에 대해 궁금한지 구체적인 약품명을 되물어보세요.\n"
            "일반적인 약학 정보를 먼저 설명하지 말고, 짧고 따뜻한 어투로 약품명을 요청하세요."
        )

    def _build_retrieval_metadata(self, search_results: list[SearchResult]) -> RetrievalMetadata:
        """Summarize the retrieval stage for persistence on user-turn metadata.

        Captures top-k medicine names/usages plus the top-1 score breakdown.
        """
        if not search_results:
            return RetrievalMetadata()
        top = search_results[0]
        return RetrievalMetadata(
            medicine_names=[r.medicine.medicine_name for r in search_results],
            medicine_usages=[r.medicine.category for r in search_results if r.medicine.category],
            top_similarity=top.vector_score,
            vector_score=top.vector_score,
            keyword_score=top.keyword_score,
            final_score=top.final_score,
        )

    def _build_sources(self, search_results: list[SearchResult]) -> list[dict]:
        """Build source payload returned to the API client.

        Args:
            search_results: Ranked MedicineInfo matches.

        Returns:
            List of lightweight source dicts.
        """
        return [
            {
                "name": r.medicine.medicine_name,
                "item_seq": r.medicine.item_seq,
                "category": r.medicine.category,
                "matched_sections": [cm.chunk.section for cm in r.matched_chunks],
                "relevance_score": round(r.final_score, 3),
            }
            for r in search_results
        ]
