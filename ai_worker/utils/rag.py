"""RAG (Retrieval-Augmented Generation) utility module.

This module provides functionality for generating medication guidance
using OpenAI's GPT models with retrieved context information.
Follows modern async patterns and error handling practices.
"""

import logging

from openai import AsyncOpenAI
from tortoise import Tortoise

from app.core.config import config

# 현재 모듈의 이름(__name__)으로 로거 생성
logger = logging.getLogger(__name__)


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
        self.model = "gpt-4o-mini"  # Model name in use
        self.embedding_model = "text-embedding-3-small"

    async def get_relevant_documents(self, query: str, limit: int = 3) -> str:
        """Get relevant documents for the given query.

        TODO: Implement actual vector DB search logic.

        Args:
            query: User query to search for relevant documents.
            limit: Maximum number of documents to retrieve.

        Returns:
            str: Retrieved context information.
        """
        # In actual implementation, perform embedding and similarity search here
        if not self.client:
            return ""

        try:
            # 1. 쿼리 임베딩 생성
            response = await self.client.embeddings.create(input=query, model=self.embedding_model)
            query_vector = response.data[0].embedding

            # 2. pgvector 코사인 유사도 검색 (Raw SQL)
            # <=> 연산자는 코사인 거리를 의미하며, 작을수록 유사함
            conn = Tortoise.get_connection("default")
            sql = """
                SELECT medicine_name, category, efficacy, side_effects, precautions
                FROM medicine_info
                ORDER BY embedding <=> $1::vector
                LIMIT $2;
            """
            results = await conn.execute_query_dict(sql, [str(query_vector), limit])

            if not results:
                return "관련된 약학 정보를 찾지 못했습니다."

            # 3. 검색된 결과를 텍스트 컨텍스트로 변환
            context_list = [
                f"[약품명: {res['medicine_name']}]\n"
                f"- 분류: {res['category']}\n"
                f"- 효능: {res['efficacy']}\n"
                f"- 부작용 및 주의사항: {res['side_effects']}, {res['precautions']}"
                for res in results
            ]

            return "\n\n".join(context_list)

        except Exception as e:
            logger.error(f"RAG Retrieval Error: {e}")
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
            # Use \n instead of actual line breaks to prevent SyntaxError
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
            # Architectural error handling: log error and provide fallback message
            # TODO: Replace with proper logging when logger is available
            logger.exception("[RAG_ERROR] Response generation failed")

            return "죄송합니다. 답변을 생성하는 중에 문제가 생겼어요.잠시 후 다시 한번 말씀해 주시겠어요?"


# Global RAG generator instance (singleton pattern for memory efficiency and state management)
rag_generator = RAGGenerator()
