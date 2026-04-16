import json
from openai import AsyncOpenAI
from tortoise import Tortoise
from app.core.config import config
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)

class RAGGenerator:
    """
    pgvector와 OpenAI를 활용하여 실제 약학 정보를 검색하고
    다정한 약사 '다약'의 답변을 생성하는 클래스입니다.
    """

    def __init__(self):
        self._api_key = config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self.model = "gpt-4o-mini"
        self.embedding_model = "text-embedding-3-small"

    async def get_relevant_documents(self, query: str, limit: int = 3) -> str:
        """
        사용자의 질문을 임베딩하여 pgvector가 적용된 DB에서 
        가장 유사한 약학 정보를 검색합니다.
        """
        if not self.client:
            return ""

        try:
            # 1. 쿼리 임베딩 생성
            response = await self.client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
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
            context_list = []
            for res in results:
                context_list.append(
                    f"[약품명: {res['medicine_name']}]\n"
                    f"- 분류: {res['category']}\n"
                    f"- 효능: {res['efficacy']}\n"
                    f"- 부작용 및 주의사항: {res['side_effects']}, {res['precautions']}"
                )
            
            return "\n\n".join(context_list)

        except Exception as e:
            logger.error(f"RAG Retrieval Error: {e}")
            return "정보 검색 중 오류가 발생했습니다."

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """
        검색된 실제 약학 컨텍스트를 결합하여 답변을 생성합니다.
        """
        try:
            if self.client is None:
                return "현재 AI 응답을 생성할 수 있는 설정이 준비되지 않았어요."

            # 1. 최신 메시지 기반 컨텍스트 확보
            user_query = messages[-1]["content"] if messages else ""
            context = await self.get_relevant_documents(user_query)

            # 2. 시스템 프롬프트 구성 (다약 페르소나 강화)
            default_system = (
                "당신은 전문적이고 다정한 약사 '다약'입니다.\n"
                "제공된 [Context]에 있는 실제 약학 정보를 바탕으로 사용자의 질문에 답변하세요.\n"
                "만약 [Context]에 질문과 관련된 정보가 없다면, 일반적인 상식선에서 답변하되 "
                "반드시 전문가와 상의할 것을 권고하세요.\n"
                "답변은 친절하고 따뜻한 말투(해요체)를 유지하세요."
            )

            instruction = system_prompt if system_prompt else default_system

            # 3. 메시지 구성
            prompt_messages = [
                {"role": "system", "content": f"{instruction}\n\n[Context]\n{context}"}
            ]
            prompt_messages.extend(messages)

            # 4. LLM 추론
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=prompt_messages,
                temperature=0.7,
                max_tokens=800,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}")
            return "죄송합니다. 답변을 생성하는 중에 문제가 생겼어요. 다시 한번 말씀해 주시겠어요?"

rag_generator = RAGGenerator()
