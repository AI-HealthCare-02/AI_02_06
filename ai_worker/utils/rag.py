"""RAG (Retrieval-Augmented Generation) utility module.

This module provides functionality for generating medication guidance
using OpenAI's GPT models with retrieved context information.
Follows modern async patterns and error handling practices.

Data Source Strategy:
- ENV=local: JSON file-based search (mock data for development)
- ENV=dev/prod: pgvector DB search (production data)
"""

import asyncio
import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from tortoise import Tortoise

from app.core.config import Env, config

logger = logging.getLogger(__name__)


def _load_medicines_from_json() -> list[dict]:
    """Load medicines data from JSON file (sync function for thread execution).

    Returns:
        List of medicine dictionaries, or empty list if file not found.
    """
    json_path = Path("/app/ai_worker/data/medicines.json")

    # Fallback for Windows local development
    if not json_path.exists():
        json_path = Path(__file__).parent.parent / "data" / "medicines.json"

    if not json_path.exists():
        return []

    with json_path.open(encoding="utf-8") as f:
        return json.load(f)


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
        self.embedding_model = "text-embedding-3-small"

    async def get_relevant_documents(self, query: str, limit: int = 3) -> str:
        """Get relevant documents for the given query.

        Uses different data sources based on environment:
        - LOCAL: JSON file-based keyword search
        - DEV/PROD: pgvector database search

        Args:
            query: User query to search for relevant documents.
            limit: Maximum number of documents to retrieve.

        Returns:
            str: Retrieved context information.
        """
        if config.ENV == Env.LOCAL:
            return await self._search_json(query, limit)
        return await self._search_db(query, limit)

    async def _search_json(self, query: str, limit: int = 3) -> str:
        """Search documents from JSON mock data (LOCAL environment).

        Args:
            query: User query to search.
            limit: Maximum number of results.

        Returns:
            str: Retrieved context from JSON data.
        """
        try:
            # Load JSON in thread to avoid blocking
            medicines = await asyncio.to_thread(_load_medicines_from_json)

            if not medicines:
                return "약물 정보 데이터를 찾을 수 없습니다."

            query_lower = query.lower()
            query_keywords = query_lower.split()

            # Keyword-based search
            matched_medicines = [
                med
                for med in medicines
                if (
                    query_lower in med["name"].lower()
                    or query_lower in med["ingredient"].lower()
                    or query_lower in med["usage"].lower()
                    or any(kw in med["name"].lower() for kw in query_keywords)
                    or any(kw in med["ingredient"].lower() for kw in query_keywords)
                )
            ]

            # Fallback keyword search
            if not matched_medicines:
                common_keywords = {
                    "진통": ["타이레놀", "이부프로펜", "아세트아미노펜"],
                    "감기": ["테라플루", "판피린", "판콜"],
                    "소화": ["까스활명수", "베아제", "가스모틴"],
                    "알레르기": ["지르텍", "클래리틴"],
                    "혈압": ["노바스크"],
                    "당뇨": ["다이아벡스"],
                    "수면": ["졸피뎀", "멜라토닌"],
                }

                for keyword, med_names in common_keywords.items():
                    if keyword in query_lower:
                        matched_medicines.extend(
                            med for med in medicines if any(name in med["name"] for name in med_names)
                        )
                        break

            matched_medicines = matched_medicines[:limit]

            if not matched_medicines:
                return "질문과 관련된 약물 정보를 찾지 못했습니다. 일반적인 의학 지식으로 답변드리겠습니다."

            return self._format_medicine_context(matched_medicines)

        except Exception:
            logger.exception("JSON search error")
            return "정보 검색 중 오류가 발생했습니다."

    async def _search_db(self, query: str, limit: int = 3) -> str:
        """Search documents from pgvector database (DEV/PROD environment).

        Args:
            query: User query to search.
            limit: Maximum number of results.

        Returns:
            str: Retrieved context from database.
        """
        if not self.client:
            return "임베딩 클라이언트가 설정되지 않았습니다."

        try:
            # 1. Generate query embedding
            response = await self.client.embeddings.create(
                input=query,
                model=self.embedding_model,
            )
            query_vector = response.data[0].embedding

            # 2. pgvector cosine similarity search
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

            # 3. Format results as context
            context_list = [
                f"[약품명: {res['medicine_name']}]\n"
                f"- 분류: {res['category']}\n"
                f"- 효능: {res['efficacy']}\n"
                f"- 부작용 및 주의사항: {res['side_effects']}, {res['precautions']}"
                for res in results
            ]

            return "\n\n".join(context_list)

        except Exception:
            logger.exception("DB search error")
            return "정보 검색 중 오류가 발생했습니다."

    def _format_medicine_context(self, medicines: list[dict]) -> str:
        """Format medicine data as context string.

        Args:
            medicines: List of medicine dictionaries.

        Returns:
            str: Formatted context string.
        """
        context_list = []
        for med in medicines:
            context = f"[약품명: {med['name']}]\n"
            context += f"- 주성분: {med['ingredient']}\n"
            context += f"- 용도: {med['usage']}\n"
            context += f"- 주의사항: {med['disclaimer']}\n"
            if med.get("contraindicated_drugs") and med["contraindicated_drugs"] != ["해당 없음"]:
                context += f"- 병용금기 약물: {', '.join(med['contraindicated_drugs'])}\n"
            if med.get("contraindicated_foods") and med["contraindicated_foods"] != ["해당 없음"]:
                context += f"- 병용금기 음식: {', '.join(med['contraindicated_foods'])}"
            context_list.append(context)

        return "\n\n".join(context_list)

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
