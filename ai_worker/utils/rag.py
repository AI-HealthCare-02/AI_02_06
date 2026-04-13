import json
import os
from pathlib import Path

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam

# 개발/배포 환경에 따른 모델 설정
_ENV = os.environ.get("APP_ENV", "dev")
_CHAT_MODEL = "gpt-4o" if _ENV == "prod" else "gpt-4o-mini"

_MEDICINES_PATH = Path(__file__).parent.parent / "data" / "medicines.json"


def _load_medicines() -> list[dict]:
    with open(_MEDICINES_PATH, encoding="utf-8") as f:
        return json.load(f)


class RAGGenerator:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = _CHAT_MODEL
        self._medicines = _load_medicines()

    async def generate_guide(self, user_medicines: list[dict], context_chunks: list[str]) -> str:
        """추출된 약 정보와 청크 데이터를 바탕으로 복약 가이드 생성"""
        context_text = "\n---\n".join(context_chunks)
        medicines_text = "\n".join(
            f"- {m['name']} ({m['ingredient']})" for m in user_medicines
        )

        prompt = f"""당신은 전문 약사 AI입니다. 아래 환자 복용 약물과 참고 데이터를 바탕으로
친절하고 상세한 복약 가이드를 작성해주세요.

[환자 복용 약물]
{medicines_text}

[참고 데이터]
{context_text}

지침:
1. 병용 금기 성분과 음식을 강조해서 알려주세요.
2. 복용 시 주의사항(면책사항)을 포함해주세요.
3. 마지막에 반드시 다음 문구를 포함하세요:
   "⚠️ 이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI API 호출 실패: {e}") from e

    async def generate_chat_response(self, question: str, history: list[dict]) -> str:
        """사용자 질문과 대화 이력을 바탕으로 복약 상담 답변 생성"""
        # 질문에서 medicines.json 키워드 매칭
        matched = [m for m in self._medicines if m["name"] in question or m["ingredient"] in question]
        if matched:
            context_text = "\n---\n".join(
                f"약 이름: {m['name']}\n성분: {m['ingredient']}\n용도: {m['usage']}\n"
                f"면책사항: {m['disclaimer']}\n병용금기 약물: {', '.join(m['contraindicated_drugs'])}\n"
                f"금기 음식: {', '.join(m['contraindicated_foods'])}"
                for m in matched
            )
        else:
            context_text = "관련 약품 데이터 없음"

        system_prompt = f"""당신은 사용자의 건강한 삶을 돕는 친절하고 전문적인 '다운포스 개인 건강 파트너'입니다. 
복약 상담뿐만 아니라 건강한 생활 습관, 영양, 운동, 그리고 전반적인 웰빙에 대해 유연하고 친절하게 답변해주세요.

지침:
1. **역할 확장**: 질문이 약과 직접적인 관련이 없더라도 사용자의 건강 증진에 도움이 되는 일반적인 건강 정보, 식단 제안, 운동 방법 등을 제공하세요.
2. **유연한 구조**: 질문의 성격에 따라 답변 형식을 조절하세요. 약 정보일 경우 [효능/용법] 위주로, 일반 건강 질문일 경우 [생활 가이드/추천 습관] 위주로 답변하세요.
3. **가독성 및 이모지**: 문단 간 명확한 줄바꿈과 이모지(💊, 🥗, 🏃‍♂️, ✨, ⚠️ 등)를 활용하여 친근하고 읽기 쉬운 스타일을 유지하세요.
4. **공감과 응원**: 사용자의 건강 고민에 공감하고 따뜻한 격려의 말을 포함하세요.
5. **마지막 문구**: 답변의 맨 마지막에는 반드시 "⚠️ 이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."를 포함하세요.

[참고 데이터 (약품 정보)]
{context_text}"""

        messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": question})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI API 호출 실패: {e}") from e
