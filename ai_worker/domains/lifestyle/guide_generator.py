"""Lifestyle guide LLM generator — pure prompt build + GPT call + parse.

Pulled out of ``app.services.lifestyle_guide_service`` so the heavy LLM call
runs in ai-worker (not the FastAPI request loop). Imports of ``app.*`` are
type/data only — no FastAPI / HTTPException dependencies live here.
"""

import hashlib

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from ai_worker.core.logger import get_logger
from app.dtos.lifestyle_guide import LlmGuideResponse
from app.services.lifestyle_guide_prompt_builder import build_guide_prompt

logger = get_logger(__name__)

_LLM_MODEL = "gpt-4o"
# 일관성 우선 — 같은 처방전 조합에는 거의 동일 출력.
_LLM_TEMPERATURE = 0.0


def _seed_for(medication_dicts: list[dict]) -> int:
    """약물 조합 기반 OpenAI seed 계산.

    같은 약물 set (이름 정렬 후 sha256) 이면 항상 같은 정수 seed 를 반환.
    OpenAI 의 ``seed`` 는 best-effort deterministic decoding 을 제공 —
    동일 (model, prompt, temperature, seed, system_fingerprint) 조합에서
    거의 동일한 출력. 캐싱이 아니므로 매 호출 비용은 그대로 발생한다.

    Args:
        medication_dicts: 활성 약물 dict 목록.

    Returns:
        2^31-1 이하의 양의 정수 (OpenAI 권장 범위).
    """
    names = sorted((m.get("medicine_name") or "") for m in medication_dicts)
    digest = hashlib.sha256("\n".join(names).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


# ── 라이프스타일 가이드 LLM 호출 ──────────────────────────────────────────
# 흐름: 활성 약물 dict 목록 -> seed 계산 -> 프롬프트 빌드
#       -> GPT 호출 (json_object, temperature=0, seed) -> JSON 검증
#       -> LlmGuideResponse 반환
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
    seed = _seed_for(medication_dicts)
    raw_json = await _call_llm(prompt, client, seed=seed)
    return _parse_response(raw_json)


async def _call_llm(prompt: str, client: AsyncOpenAI, *, seed: int) -> str:
    """OpenAI ``chat.completions`` json_object 호출 (deterministic 강화)."""
    try:
        response = await client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=_LLM_TEMPERATURE,
            seed=seed,
        )
        if response.system_fingerprint:
            logger.info(
                "[GUIDE] LLM 호출 seed=%d fingerprint=%s",
                seed,
                response.system_fingerprint,
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
