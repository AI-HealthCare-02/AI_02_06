"""Lifestyle guide LLM generator — pure prompt build + GPT call + parse.

Pulled out of ``app.services.lifestyle_guide_service`` so the heavy LLM call
runs in ai-worker (not the FastAPI request loop). Imports of ``app.*`` are
type/data only — no FastAPI / HTTPException dependencies live here.
"""

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from ai_worker.core.logger import get_logger
from app.dtos.lifestyle_guide import LlmGuideResponse
from app.services.lifestyle_guide_prompt_builder import build_guide_prompt

logger = get_logger(__name__)

_LLM_MODEL = "gpt-4o-mini"
_LLM_TEMPERATURE = 0.3


# ── 라이프스타일 가이드 LLM 호출 ──────────────────────────────────────────
# 흐름: 활성 약물 dict 목록 -> 프롬프트 빌드 -> GPT 호출 (json_object)
#       -> JSON 검증 -> LlmGuideResponse 반환
async def generate_guide_payload(
    medication_dicts: list[dict],
    client: AsyncOpenAI,
) -> LlmGuideResponse:
    """Build prompt, call GPT, validate JSON.

    Args:
        medication_dicts: Snapshot-safe dict list of active medications.
        client: Pre-instantiated ``AsyncOpenAI`` client (caller owns lifecycle).

    Returns:
        Parsed + validated ``LlmGuideResponse``.

    Raises:
        ValueError: LLM call or JSON parse failure (caller decides terminal status).
    """
    prompt = build_guide_prompt(medication_dicts)
    raw_json = await _call_llm(prompt, client)
    return _parse_response(raw_json)


async def _call_llm(prompt: str, client: AsyncOpenAI) -> str:
    """OpenAI ``chat.completions`` json_object 호출."""
    try:
        response = await client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=_LLM_TEMPERATURE,
        )
        return response.choices[0].message.content or ""
    except OpenAIError as e:
        logger.exception("[GUIDE] GPT 호출 실패")
        raise ValueError(f"가이드 생성 실패: LLM 호출 오류 — {e}") from e


def _parse_response(raw_json: str) -> LlmGuideResponse:
    """Validate raw GPT JSON string into typed ``LlmGuideResponse``."""
    try:
        return LlmGuideResponse.model_validate_json(raw_json)
    except (ValidationError, ValueError) as e:
        logger.warning("[GUIDE] GPT 응답 파싱 실패 — %s", e)
        raise ValueError(f"가이드 생성 실패: LLM 응답 파싱 오류 — {e}") from e
