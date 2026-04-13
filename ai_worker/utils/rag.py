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

핵심 원칙:
- **약품/복약 질문이 최우선**입니다. 질문이 약(약 이름/성분/용법/부작용/상호작용/금기/복용 시간/병용 등)과 관련되면 가장 먼저, 가장 자세히 답변하세요.
- 약과 직접 관련이 없는 질문도 **일상 대화/건강 상담 범위에서 친절하게 답변**할 수 있습니다. 다만 의료 행위(진단/처방/치료 지시)는 하지 말고, 필요 시 전문의 상담을 권유하세요.

답변 규칙:
1. **우선순위**: (1) 약/복약 → (2) 건강 생활습관(운동/영양/수면/스트레스) → (3) 일반적인 일상 대화(짧고 친절하게).
2. **근거 사용**: 아래 [참고 데이터]에 있는 약품 정보가 있으면 최우선으로 활용하고, 없으면 일반적인 약학/건강 지식으로 답하되 단정하지 마세요.
3. **형식**:
   - 약 질문이면: [핵심 요약] → [복용 방법] → [주의/금기] → [언제 병원/약사 상담?] 순서로 간결하게.
   - 일반 건강 질문이면: [핵심 요약] → [추천 습관 3개] → [주의점] 순서로.
   - 일상 대화면: 2~5문장으로 답하고, 사용자의 맥락이 건강/복약이면 자연스럽게 한 질문으로 이어가세요.
4. **안전 문구**: 답변의 맨 마지막에는 반드시 다음 문구를 포함하세요.
   "⚠️ 이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."

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
