from openai import AsyncOpenAI

from app.core.config import config


class RAGGenerator:
    """
    RAG(Retrieval-Augmented Generation)를 통해
    다정한 약사 '다약'의 답변을 생성하는 클래스입니다.
    """

    def __init__(self):
        # API Key가 없는 환경(테스트/CI)에서도 모듈 import가 깨지지 않도록 lazy 처리합니다.
        self._api_key = config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self.model = "gpt-4o-mini"  # 혹은 사용 중인 모델명

    async def get_relevant_documents(self, query: str) -> str:
        """
        [TODO] 실제 벡터 DB(Pinecone, Chroma 등)에서 관련 문서를 검색하는 로직
        현재는 실전 프로젝트 구조를 위해 Mock 데이터 혹은 빈 문자열을 반환합니다.
        """
        # 실제 구현 시 여기서 임베딩 후 유사도 검색을 수행합니다.
        context = "환자는 현재 복용 중인 약물에 대한 부작용을 걱정하고 있습니다."
        return context

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """
        사용자의 메시지 히스토리와 검색된 컨텍스트를 결합하여 답변을 생성합니다.
        """
        try:
            if self.client is None:
                return (
                    "현재 AI 응답을 생성할 수 있는 설정이 준비되지 않았어요. "
                    "관리자에게 OPENAI_API_KEY 설정을 요청해 주시겠어요?"
                )

            # 1. 컨텍스트 확보 (가장 최근 메시지 기준)
            user_query = messages[-1]["content"] if messages else ""
            context = await self.get_relevant_documents(user_query)

            # 2. 시스템 프롬프트 설정 (전달받은 값이 없으면 기본값 사용)
            # SyntaxError 방지를 위해 실제 줄바꿈 대신 \n 사용
            default_system = (
                "당신은 전문적이고 다정한 약사 '다약'입니다.\n"
                "제공된 [Context]를 바탕으로 사용자의 질문에 친절하게 답변하세요.\n"
                "모든 답변은 의학적 근거를 바탕으로 하되, 따뜻한 말투를 유지하세요."
            )

            instruction = system_prompt if system_prompt else default_system

            # 3. OpenAI API 호출을 위한 메시지 구성
            prompt_messages = [{"role": "system", "content": f"{instruction}\n\n[Context]\n{context}"}]
            prompt_messages.extend(messages)

            # 4. LLM 추론
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=prompt_messages,
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content

        except Exception as e:
            # 아키텍처 관점에서의 에러 핸들링: 로그를 남기고 사용자에게는 Fallback 메시지 전달
            print(f"[RAG_ERROR] 답변 생성 실패: {str(e)}")
            return "죄송합니다. 잠시 서버에 혼선이 생겼어요. 약사님이 잠시 자리를 비우신 것 같아요. 다시 한번 말씀해 주시겠어요?"


# 싱글톤 패턴으로 인스턴스 제공 (메모리 효율 및 상태 관리)
rag_generator = RAGGenerator()
