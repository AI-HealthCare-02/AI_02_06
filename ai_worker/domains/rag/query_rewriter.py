"""대화 맥락 기반 쿼리 재작성.

다중 턴 한국어 질의에 들어 있는 대명사·생략된 주어·지시어를 이력에서
실제 약품명으로 치환해 self-contained 한 단일 쿼리로 만든다. 이력에서
참조 대상을 특정할 수 없으면 ``UNRESOLVABLE`` 을 반환해 호출자가 clarify
프롬프트로 분기하게 한다.
"""

import logging
import re
import time

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion as OpenAIChatCompletion

from ai_worker.core.openai_client import get_openai_client
from ai_worker.core.text_helpers import (
    format_token_usage,
    sanitize_error_message,
    strip_quote_wrapping,
)
from ai_worker.domains.rag.prompt_builder import (
    REWRITE_SYSTEM_PROMPT,
    build_rewrite_user_prompt,
)
from app.dtos.rag import RewriteResult, RewriteStatus, TokenUsage

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"
_TEMPERATURE = 0.0
_MAX_TOKENS = 200
_UNRESOLVABLE_PATTERN = re.compile(r"^\W*unresolvable\W*$", re.IGNORECASE)


async def rewrite_user_query(history: list[dict[str, str]], current_query: str) -> RewriteResult:
    """다중 턴 쿼리를 self-contained 한 한 문장으로 재작성한다.

    Args:
        history: 시간순(오래된 것 먼저) 대화 턴.
        current_query: 사용자의 이번 턴 쿼리.

    Returns:
        ``RewriteResult`` — status (OK/UNRESOLVABLE/FALLBACK), 최종 쿼리, 토큰 사용량.
    """
    client = get_openai_client()
    if client is None:
        logger.error("[RAG] rewrite: api_error type=NoClient; fallback to original query")
        return _fallback(current_query, token_usage=None)

    user_prompt = build_rewrite_user_prompt(history, current_query)
    response, elapsed_ms = await _call_llm(client, user_prompt)
    if response is None:
        return _fallback(current_query, token_usage=None)

    return _parse_response(response, elapsed_ms, current_query)


async def _call_llm(client: AsyncOpenAI, user_prompt: str) -> tuple[OpenAIChatCompletion | None, int]:
    """OpenAI API 호출. 실패 시 ``(None, elapsed_ms)`` 반환."""
    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "[RAG] rewrite: api_error type=%s msg=%s after %dms; fallback to original query",
            type(exc).__name__,
            sanitize_error_message(str(exc)),
            elapsed_ms,
        )
        return None, elapsed_ms
    return response, int((time.perf_counter() - start) * 1000)


def _parse_response(response: OpenAIChatCompletion, elapsed_ms: int, current_query: str) -> RewriteResult:
    """LLM 응답을 파싱해 RewriteResult 로 변환."""
    raw = response.choices[0].message.content or ""
    cleaned = strip_quote_wrapping(raw)
    token_usage = _extract_token_usage(response)

    if not cleaned:
        logger.warning("[RAG] rewrite: empty response after %dms; fallback to original query", elapsed_ms)
        return _fallback(current_query, token_usage=token_usage)

    if _UNRESOLVABLE_PATTERN.match(cleaned):
        logger.warning(
            "[RAG] rewrite: unresolvable (no anchor in history); clarify path tokens=%s took=%dms",
            format_token_usage(token_usage),
            elapsed_ms,
        )
        return RewriteResult(status=RewriteStatus.UNRESOLVABLE, query=current_query, token_usage=token_usage)

    logger.info(
        "[RAG] rewrite: ok %r -> %r tokens=%s took=%dms",
        current_query,
        cleaned,
        format_token_usage(token_usage),
        elapsed_ms,
    )
    return RewriteResult(status=RewriteStatus.OK, query=cleaned, token_usage=token_usage)


def _extract_token_usage(response: OpenAIChatCompletion) -> TokenUsage | None:
    """response.usage 가 있으면 TokenUsage DTO 로 변환."""
    if response.usage is None:
        return None
    return TokenUsage(
        model=_MODEL,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
    )


def _fallback(current_query: str, token_usage: TokenUsage | None) -> RewriteResult:
    """API 실패 또는 빈 응답 시 원본 쿼리로 fallback."""
    return RewriteResult(status=RewriteStatus.FALLBACK, query=current_query, token_usage=token_usage)
