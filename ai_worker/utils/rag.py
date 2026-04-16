"""RAG (Retrieval-Augmented Generation) utility module.

This module provides functionality for generating medication guidance
using OpenAI's GPT models with retrieved context information.
Follows modern async patterns and error handling practices.
"""

import logging

from openai import AsyncOpenAI

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

    async def get_relevant_documents(self, _query: str) -> str:
        """Get relevant documents for the given query.

        TODO: Implement actual vector DB (Pinecone, Chroma, etc.) search logic.
        Currently returns mock data or empty string for project structure.

        Args:
            _query: User query to search for relevant documents (unused in mock).

        Returns:
            str: Retrieved context information.
        """
        # In actual implementation, perform embedding and similarity search here
        context = "The patient is concerned about side effects of currently taking medications."
        return context

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
                return (
                    "AI response generation is currently not available. "
                    "Please ask the administrator to configure OPENAI_API_KEY."
                )

            # 1. Get context (based on most recent message)
            user_query = messages[-1]["content"] if messages else ""
            context = await self.get_relevant_documents(user_query)

            # 2. Set system prompt (use default if not provided)
            # Use \n instead of actual line breaks to prevent SyntaxError
            default_system = (
                "You are a professional and caring pharmacist 'Dayak'.\n"
                "Answer user questions kindly based on the provided [Context].\n"
                "All answers should be based on medical evidence while maintaining a warm tone."
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
                max_tokens=500,
            )

            return response.choices[0].message.content

        except Exception:
            # Architectural error handling: log error and provide fallback message
            # TODO: Replace with proper logging when logger is available
            logger.exception("[RAG_ERROR] Response generation failed")

            return (
                "Sorry, there seems to be a temporary server issue. "
                "The pharmacist seems to be away for a moment. Could you please try again?"
            )


# Global RAG generator instance (singleton pattern for memory efficiency and state management)
rag_generator = RAGGenerator()
