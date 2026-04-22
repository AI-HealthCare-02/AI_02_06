"""LLM response generation for the RAG pipeline.

This module is the LLM generation stage only. Retrieval is owned by
`app.services.rag.retrievers.hybrid.HybridRetriever` and `app.services.rag.
pipeline.RAGPipeline._build_context`; the caller must pass the prepared
context inside `system_prompt`. The generator itself does not touch the
database or the embedding model.
"""

import logging

from openai import AsyncOpenAI

from app.core.config import config

logger = logging.getLogger(__name__)


class RAGGenerator:
    """OpenAI-backed chat response generator for the 'Dayak' pharmacist persona."""

    def __init__(self) -> None:
        """Initialize the generator with a lazily-configured OpenAI client."""
        self._api_key = config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self.model = "gpt-4o-mini"

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Generate a chat response from prior messages and a prepared system prompt.

        Args:
            messages: Prior conversation turns (user/assistant) ending with
                the current user question.
            system_prompt: Fully prepared system prompt. Callers supply the
                retrieved context inside this string. When None, a persona-only
                fallback prompt with no retrieval context is used.

        Returns:
            Generated assistant reply, or a fallback message when the API key
            is missing.
        """
        if self.client is None:
            return "현재 AI 응답을 생성할 수 있는 설정이 준비되지 않았어요."

        default_system = (
            "You are 'Dayak,' a professional and warm-hearted pharmacist.\n"
            "Answer the user's questions based on the pharmaceutical information "
            "provided inside the prompt. If the prompt contains no relevant "
            "context, answer from general medical knowledge and strongly advise "
            "consulting a professional.\n"
            "Maintain a kind and warm tone (using the 'Haeyo-che' style)."
        )
        instruction = system_prompt or default_system

        prompt_messages = [{"role": "system", "content": instruction}, *messages]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=prompt_messages,
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content
