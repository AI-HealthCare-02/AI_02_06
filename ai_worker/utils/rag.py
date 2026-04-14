import json
import os
import asyncio
from pathlib import Path

from openai import AsyncOpenAI, OpenAI, OpenAIError

# ai_worker logger 임포트
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)

# 개발/배포 환경에 따른 모델 설정
_ENV = os.environ.get("APP_ENV", "dev")
_CHAT_MODEL = "gpt-4o" if _ENV == "prod" else "gpt-4o-mini"

_MEDICINES_PATH = Path(__file__).parent.parent / "data" / "medicines.json"


def _load_medicines() -> list[dict]:
    try:
        with open(_MEDICINES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


class RAGGenerator:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            try:
                from app.core.config import config as app_config
                api_key = app_config.OPENAI_API_KEY
            except Exception:
                api_key = None

        if not api_key:
            try:
                from ai_worker.core.config import config as worker_config
                api_key = worker_config.OPENAI_API_KEY
            except Exception:
                api_key = None

        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

        self.client = AsyncOpenAI(api_key=api_key)
        self._sync_client = OpenAI(api_key=api_key)
        self.model = _CHAT_MODEL
        self._medicines = _load_medicines()

    def generate_guide(self, user_medicines: list[dict], context_chunks: list[str]) -> str:
        """추출된 약 정보와 청크 데이터를 바탕으로 복약 가이드 생성"""
        # 줄바꿈 에러 방지를 위해 \n 명시적 사용
        context_text = "\n---\n".join(context_chunks)
        medicines_text = "\n".join(f"- {m['name']} ({m['ingredient']})" for m in user_medicines)

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
   "이 안내는 참고용이며, 정확한 진단과 처방은 반드시 전문 의료인과 상의하십시오."
"""

        try:
            response = self._sync_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI API 호출 실패: {e}") from e

    async def generate_chat_response(self, question: str, history: list[dict],
                                     context_chunks: list[str] | None = None,
                                     system_prompt: str | None = None) -> str:
        """
        사용자 질문과 대화 이력을 바탕으로 복약 상담 답변 생성
        system_prompt: FastAPI 등 외부에서 주입되는 시스템 메시지 (TypeError 방지)
        """

        # 1. 외부 검색 결과(RAG) 처리
        retrieved_context_text = ""
        if context_chunks:
            retrieved_context_text = "\n---\n".join(context_chunks)

        # 2. 내부 medicines.json 데이터 매칭
        matched_medicines_text = []
        if self._medicines:
            question_lower = question.lower()
            for m in self._medicines:
                if (m.get("name", "").lower() in question_lower or
                        m.get("ingredient", "").lower() in question_lower or
                        m.get("usage", "").lower() in question_lower):
                    matched_medicines_text.append(
                        f"약 이름: {m.get('name', '정보 없음')}\n"
                        f"성분: {m.get('ingredient', '정보 없음')}\n"
                        f"용도: {m.get('usage', '정보 없음')}\n"
                        f"면책사항: {m.get('disclaimer', '정보 없음')}\n"
                        f"병용금기 약물: {', '.join(m.get('contraindicated_drugs', [])) if m.get('contraindicated_drugs') else '없음'}\n"
                        f"금기 음식: {', '.join(m.get('contraindicated_foods', [])) if m.get('contraindicated_foods') else '없음'}"
                    )

        medicine_context_str = "\n---\n".join(matched_medicines_text) if matched_medicines_text else "관련 약품 데이터 없음"

        # 3. 컨텍스트 통합
        full_context_text = ""
        if retrieved_context_text:
            full_context_text += f"[외부 검색 결과]\n{retrieved_context_text}\n"
        if medicine_context_str != "관련 약품 데이터 없음":
            full_context_text += f"[약품 정보]\n{medicine_context_str}"
        else:
            full_context_text += "[약품 정보]\n관련 약품 데이터 없음"

        # 4. 최종 시스템 프롬프트 결정 (주입된 프롬프트 우선)
        if system_prompt:
            final_system_prompt = f"{system_prompt}\n\n[참고 컨텍스트]\n{full_context_text}"
        else:
            final_system_prompt = (
                "당신은 사용자의 건강을 진심으로 걱정하는 '다정한 퍼스널 약사'입니다.\n"
                "제공된 [컨텍스트] 정보를 바탕으로 답변하되, 정보가 없더라도 친절하게 조언해주세요.\n"
                "말투는 반드시 부드러운 구어체(~해요, ~일까요?)를 사용하고 따뜻한 위로를 곁들여주세요.\n\n"
                f"[컨텍스트]\n{full_context_text}"
            )

        # 5. 메시지 구성
        messages = [{"role": "system", "content": final_system_prompt}]
        for h in history:
            # history 딕셔너리 키 값 안전하게 추출
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": question})

        # --- Retry Logic ---
        MAX_RETRIES = 3
        DELAY_SECONDS = 2
        retries = 0
        last_error = None

        while retries < MAX_RETRIES:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                )
                return response.choices[0].message.content or ""
            except OpenAIError as e:
                last_error = e
                logger.warning(f"OpenAI API 호출 실패 (Retry {retries + 1}/{MAX_RETRIES}): {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    await asyncio.sleep(DELAY_SECONDS)
            except Exception as e:
                logger.error(f"예상치 못한 오류 발생: {e}")
                raise RuntimeError(f"응답 생성 중 시스템 오류: {e}") from e

        if last_error:
            logger.error(f"최대 재시도 횟수 초과: {last_error}")
            raise RuntimeError(f"AI 응답 생성 실패 (OpenAI): {last_error}") from last_error

        raise RuntimeError("알 수 없는 이유로 응답 생성에 실패했습니다.")
