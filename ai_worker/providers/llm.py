"""AI-Worker LLM provider (OpenAI).

Centralises all OpenAI chat completion calls inside AI-Worker so that
FastAPI never constructs an ``AsyncOpenAI`` client. A single
``RAGGenerator`` (which owns an ``AsyncOpenAI`` client + prompt
templates) is reused across every RQ job call, eliminating per-request
client allocation and keeping connection pools warm.

The results are converted to plain ``dict`` before return so that RQ
can serialize them safely via pickle / JSON on its internal transport.
"""

import logging
from typing import Any

from ai_worker.utils.rag import RAGGenerator
from app.dtos.rag import RewriteStatus

logger = logging.getLogger(__name__)


# ── 프로세스 싱글톤 ─────────────────────────────────────────────
_generator: RAGGenerator | None = None


def _get_generator() -> RAGGenerator:
    """Return the process-wide ``RAGGenerator``, creating it on first use."""
    global _generator
    if _generator is None:
        _generator = RAGGenerator()
        logger.info("RAGGenerator singleton initialised (model=%s)", _generator.model)
    return _generator


# ── 공개 API ───────────────────────────────────────────────────


async def rewrite_query(history: list[dict[str, str]], current_query: str) -> dict[str, Any]:
    """Rewrite a multi-turn Korean query into a self-contained one.

    Args:
        history: Prior conversation turns (oldest first).
        current_query: User's latest query text.

    Returns:
        ``{"status", "query", "token_usage"}`` dict. ``status`` is one of
        ``"ok" | "unresolvable" | "fallback"``.
    """
    result = await _get_generator().rewrite_query(history=history, current_query=current_query)
    return {
        "status": result.status.value if isinstance(result.status, RewriteStatus) else str(result.status),
        "query": result.query,
        "token_usage": result.token_usage.model_dump() if result.token_usage is not None else None,
    }


async def generate_chat_response(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Generate a chat answer from prior messages + prepared system prompt.

    Args:
        messages: Chronological chat turns ending with the user's latest.
        system_prompt: Fully-prepared system prompt (context already inlined).

    Returns:
        ``{"answer", "token_usage"}`` dict.
    """
    result = await _get_generator().generate_chat_response(messages, system_prompt=system_prompt)
    return {
        "answer": result.answer,
        "token_usage": result.token_usage.model_dump() if result.token_usage is not None else None,
    }
