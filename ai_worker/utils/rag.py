"""RAG (Retrieval-Augmented Generation) utility module.

This module provides functionality for generating medication guidance
using OpenAI's GPT models with retrieved context information.
Follows modern async patterns and error handling practices.

Uses pgvector database for vector similarity search with SentenceTransformer.
"""

import asyncio
import logging

import numpy as np
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
from tortoise import Tortoise

from app.core.config import config

logger = logging.getLogger(__name__)

# Embedding model configuration (same as seeding script)
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
EMBEDDING_DIMENSIONS = 768

# Global embedding model (initialized lazily)
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Get or initialize embedding model synchronously.

    Uses the already-loaded model from SentenceTransformerProvider if available,
    to avoid loading the model twice.

    Returns:
        SentenceTransformer: Embedding model instance.
    """
    global _embedding_model
    if _embedding_model is None:
        # Try to reuse the already-initialized provider model first
        try:
            from app.services.rag.providers.sentence_transformer import _provider

            if _provider is not None and _provider.model is not None:
                _embedding_model = _provider.model
                logger.info("Reusing already-loaded embedding model from SentenceTransformerProvider")
                return _embedding_model
        except ImportError:
            pass

        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def _normalize_vector(vector: list[float]) -> list[float]:
    """L2-normalize a vector for cosine similarity.

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


class RAGGenerator:
    """RAG generator for creating friendly pharmacist responses.

    This class generates responses from a friendly pharmacist character 'Dayak'
    using Retrieval-Augmented Generation techniques with modern async patterns.
    """

    def __init__(self) -> None:
        """Initialize RAG generator with OpenAI client.

        API Key is handled lazily to prevent import failures
        in test/CI environments without API keys.
        """
        self._api_key = config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self.model = "gpt-4o-mini"

    async def get_relevant_documents(self, query: str, limit: int = 3) -> str:
        """Get relevant documents for the given query using pgvector similarity search.

        Args:
            query: User query to search for relevant documents.
            limit: Maximum number of documents to retrieve.

        Returns:
            str: Retrieved context information.
        """
        try:
            # 1. Generate query embedding using SentenceTransformer
            model = _get_embedding_model()
            embedding = await asyncio.get_event_loop().run_in_executor(None, model.encode, query)
            query_vector = _normalize_vector(embedding.tolist())

            # 2. pgvector cosine similarity search on document_chunks
            conn = Tortoise.get_connection("default")
            sql = """
                SELECT
                    dc.section_title,
                    dc.content,
                    dc.keywords,
                    1 - (dc.embedding <=> $1::vector) as similarity
                FROM document_chunks dc
                ORDER BY dc.embedding <=> $1::vector
                LIMIT $2;
            """
            results = await conn.execute_query_dict(sql, [str(query_vector), limit])

            if not results:
                return "관련된 약학 정보를 찾지 못했습니다."

            # 3. Format results as context with similarity score
            context_list = []
            for res in results:
                similarity_pct = round(res["similarity"] * 100, 1)
                context = f"[{res['section_title']}] (유사도: {similarity_pct}%)\n{res['content']}"
                context_list.append(context)
                logger.info(f"Retrieved: {res['section_title']} (similarity: {similarity_pct}%)")

            return "\n\n".join(context_list)

        except Exception:
            logger.exception("DB search error")
            return "정보 검색 중 오류가 발생했습니다."

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Generate chat response using user message history and retrieved context.

        Args:
            messages: List of message dictionaries with role and content.
            system_prompt: Optional custom system prompt.

        Returns:
            str: Generated response from the AI pharmacist.
        """
        try:
            if self.client is None:
                return "현재 AI 응답을 생성할 수 있는 설정이 준비되지 않았어요."

            # 1. Get context (based on most recent message)
            user_query = messages[-1]["content"] if messages else ""
            context = await self.get_relevant_documents(user_query)

            # 2. Set system prompt (use default if not provided)
            default_system = (
                "You are 'Dayak,' a professional and warm-hearted pharmacist.\n"
                "Please answer the user's questions based on the actual "
                "pharmaceutical information provided in the [Context].\n"
                "If the [Context] does not contain information related to the question, "
                "answer based on general medical knowledge but strictly advise "
                "the user to consult with a professional.\n"
                "Maintain a kind and warm tone (using the 'Haeyo-che' style) "
                "throughout your response."
            )

            instruction = system_prompt or default_system

            # 3. Construct messages for OpenAI API call
            prompt_messages = [{"role": "system", "content": f"{instruction}\n\n[Context]\n{context}"}]
            prompt_messages.extend(messages)

            # 4. LLM inference
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=prompt_messages,
                temperature=0.7,
                max_tokens=800,
            )

            return response.choices[0].message.content

        except Exception:
            logger.exception("[RAG_ERROR] Response generation failed")
            return "죄송합니다. 답변을 생성하는 중에 문제가 생겼어요. 잠시 후 다시 한번 말씀해 주시겠어요?"


# Global RAG generator instance (singleton pattern)
rag_generator = RAGGenerator()
