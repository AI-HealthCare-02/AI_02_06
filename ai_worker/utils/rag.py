"""LLM response generation for the RAG pipeline.

This module is the LLM generation stage only. Retrieval is owned by
`app.services.rag.retrievers.hybrid.HybridRetriever` and `app.services.rag.
pipeline.RAGPipeline._build_context`; the caller must pass the prepared
context inside `system_prompt`. The generator itself does not touch the
database or the embedding model.

It also owns the query-rewrite stage: `rewrite_query` turns a multi-turn
Korean query with pronouns / elided subjects into a self-contained single
query using the conversation history.
"""

import logging
import re
import time

from openai import AsyncOpenAI

from app.core.config import config
from app.dtos.rag import ChatCompletion, RewriteResult, RewriteStatus, TokenUsage

logger = logging.getLogger(__name__)

_UNRESOLVABLE_PATTERN = re.compile(r"^\W*unresolvable\W*$", re.IGNORECASE)

_REWRITE_SYSTEM_PROMPT = (
    "당신은 한국어 의료 상담 대화의 쿼리 재작성기입니다.\n"
    "대화 이력과 현재 질의를 받아 self-contained 한 문장 한국어 쿼리로 재작성하세요.\n"
    "대명사(그 약, 이 약, 저것, 그것, 해당 약), 생략된 주어, 지시어(아까, 방금)는 "
    "이력에서 실제 약품명으로 치환합니다.\n"
    "복수 지시(그 약들, 둘 다, 두 약)는 이력에서 해당 약품들을 모두 포함해 재작성합니다.\n"
    "\n"
    "중요:\n"
    "- 현재 질의가 참조를 포함하지만 이력에서 참조 대상을 특정할 수 없으면, "
    "재작성하지 말고 정확히 다음 문자열만 출력: UNRESOLVABLE\n"
    "- 현재 질의가 이미 self-contained 하면 그대로 출력해도 됩니다.\n"
    "- 설명, 접두사, 인용부호 없이 한 문장만 출력하세요."
)


def _sanitize_error(message: str, limit: int = 120) -> str:
    """Collapse whitespace and cap error messages so logs stay one-liner."""
    cleaned = " ".join(message.split())
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "..."


def _strip_wrapping(text: str) -> str:
    """Strip surrounding whitespace and paired quotes an LLM may add."""
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
        stripped = stripped[1:-1].strip()
    return stripped


class RAGGenerator:
    """OpenAI-backed chat response generator for the 'Dayak' pharmacist persona."""

    def __init__(self) -> None:
        """Initialize the generator with a lazily-configured OpenAI client."""
        self._api_key = config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self.model = "gpt-4o-mini"

    async def rewrite_query(
        self,
        history: list[dict[str, str]],
        current_query: str,
    ) -> RewriteResult:
        """Rewrite a multi-turn query into a self-contained single query.

        Outcomes:
          - OK: LLM returned a usable rewritten query.
          - UNRESOLVABLE: LLM signaled no anchor exists in history; caller
            should switch to a clarify prompt instead of retrieval.
          - FALLBACK: Technical failure (no client, API exception, empty
            output). Caller should use the original query verbatim.

        Args:
            history: Chronological (oldest first) turns for rewrite context.
            current_query: The user's latest query text.

        Returns:
            RewriteResult carrying status, effective query, and token usage.
        """
        if self.client is None:
            logger.error("[RAG] rewrite: api_error type=NoClient; fallback to original query")
            return RewriteResult(status=RewriteStatus.FALLBACK, query=current_query, token_usage=None)

        history_lines = [f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in history]
        history_block = "\n".join(history_lines) if history_lines else "(없음)"
        user_prompt = f"이력:\n{history_block}\n\n현재 질의:\n{current_query}\n\n재작성:"

        start = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=200,
            )
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "[RAG] rewrite: api_error type=%s msg=%s after %dms; fallback to original query",
                type(e).__name__,
                _sanitize_error(str(e)),
                elapsed_ms,
            )
            return RewriteResult(status=RewriteStatus.FALLBACK, query=current_query, token_usage=None)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        raw = response.choices[0].message.content or ""
        cleaned = _strip_wrapping(raw)
        token_usage: TokenUsage | None = None
        if response.usage is not None:
            token_usage = TokenUsage(
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        if not cleaned:
            logger.warning("[RAG] rewrite: empty response after %dms; fallback to original query", elapsed_ms)
            return RewriteResult(status=RewriteStatus.FALLBACK, query=current_query, token_usage=token_usage)

        if _UNRESOLVABLE_PATTERN.match(cleaned):
            logger.warning(
                "[RAG] rewrite: unresolvable (no anchor in history); clarify path tokens=%s took=%dms",
                _fmt_tokens(token_usage),
                elapsed_ms,
            )
            return RewriteResult(status=RewriteStatus.UNRESOLVABLE, query=current_query, token_usage=token_usage)

        logger.info(
            "[RAG] rewrite: ok %r -> %r tokens=%s took=%dms",
            current_query,
            cleaned,
            _fmt_tokens(token_usage),
            elapsed_ms,
        )
        return RewriteResult(status=RewriteStatus.OK, query=cleaned, token_usage=token_usage)

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> ChatCompletion:
        """Generate a chat response from prior messages and a prepared system prompt.

        Args:
            messages: Prior conversation turns (user/assistant) ending with
                the current user question.
            system_prompt: Fully prepared system prompt. Callers supply the
                retrieved context inside this string. When None, a persona-only
                fallback prompt with no retrieval context is used.

        Returns:
            ChatCompletion carrying the answer and (when available) token usage.
            When the API key is missing, returns a fallback answer with
            token_usage=None.
        """
        if self.client is None:
            return ChatCompletion(
                answer="현재 AI 응답을 생성할 수 있는 설정이 준비되지 않았어요.",
                token_usage=None,
            )

        default_system = (
            "You are 'Dayak,' a professional and warm-hearted pharmacist.\n"
            "Answer the user's questions based on the pharmaceutical information "
            "provided inside the prompt. If the prompt contains no relevant "
            "context, answer from general medical knowledge and strongly advise "
            "consulting a professional.\n"
            "Maintain a kind and warm tone (using the 'Haeyo-che' style)."
        )
        instruction = system_prompt or default_system

        prompt_messages = [{"role": "system", "content": instruction}, *messages]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=prompt_messages,
            temperature=0.7,
            max_tokens=800,
        )
        answer = response.choices[0].message.content
        usage = None
        if response.usage is not None:
            usage = TokenUsage(
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        return ChatCompletion(answer=answer, token_usage=usage)


def _fmt_tokens(usage: TokenUsage | None) -> str:
    """Compact token usage representation for log lines."""
    if usage is None:
        return "?"
    return f"{usage.total_tokens}({usage.prompt_tokens}+{usage.completion_tokens})"
