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
from app.dtos.rag import (
    ChatCompletion,
    RewriteResult,
    RewriteStatus,
    SummaryResult,
    SummaryStatus,
    TokenUsage,
)

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

_SUMMARY_SYSTEM_PROMPT = (
    "# Role\n"
    "당신은 복약·건강 상담 대화의 기록관입니다. 이후의 답변 품질을 위해 지나간 "
    "대화의 의료적 맥락만을 정확히 보존하는 것이 임무입니다.\n"
    "\n"
    "# Rule\n"
    "- 출력은 한국어 GitHub-Flavored Markdown 으로 작성합니다. 코드블록(```)이나 "
    "JSON 래핑은 금지합니다 — 마크다운 본문만 그대로 출력합니다.\n"
    "- 의료·복약 맥락에 **무관한 내용**(인사, 잡담, 주제 밖 질문, 시스템 오류 메시지)은 "
    "무조건 제외합니다.\n"
    "- 사용자가 언급한 **약품명 / 증상 / 알레르기 / 기저질환 / 복용 스케줄·용량**은 "
    "원문 표기를 유지하며 빠짐없이 포함합니다.\n"
    "- 시간 순서를 보존합니다. 상반된 발언이 있으면 **최근 발언을 우선**하고, "
    "과거 발언이 번복됐음을 한 문장으로 표기합니다.\n"
    "- 원문에 없는 사실을 추측·창작하지 않습니다. 확실하지 않으면 "
    '"사용자가 언급함" 수준으로만 남깁니다.\n'
    "- 의사의 진단과 사용자의 자기 추측은 구분해서 기록합니다.\n"
    "- 개인정보 중 이름 이외의 민감정보(전화번호, 주민번호, 주소 상세)는 마스킹합니다.\n"
    "\n"
    "# Task\n"
    "아래 **[이전 요약]**(있다면)과 **[새 대화 로그]**를 합쳐 하나의 통합 마크다운 "
    "요약을 작성합니다. 이전 요약의 사실이 새 대화에서 번복되면 갱신하고, 보강되면 "
    "병합합니다.\n"
    "\n"
    "# Output Format\n"
    "다음 섹션 구조를 따르는 마크다운으로 출력합니다. 해당 정보가 없는 섹션은 "
    "통째로 생략합니다 (빈 섹션을 남기지 않습니다).\n"
    "\n"
    "```\n"
    "## 한 줄 요약\n"
    "현재 사용자가 관리 중인 약·건강 이슈 한 줄.\n"
    "\n"
    "## 복용 중인 약\n"
    "- **약품명**: 용량 / 스케줄 / 관련 증상\n"
    "\n"
    "## 증상 및 호소\n"
    "- 호소 내용 (시점 포함)\n"
    "\n"
    "## 알레르기·기저질환\n"
    "- 해당 항목\n"
    "\n"
    "## 주의 이력\n"
    "- 이전 상담에서 경고되었던 상호작용·부작용\n"
    "```\n"
    "\n"
    "- 전체 길이는 300자 이내로 유지합니다.\n"
    "- 메타 코멘트(예: '요약 시점 메시지 N개 반영') 없이 본문만 출력합니다.\n"
    "- 코드블록 펜스(```)는 위 구조 예시에만 사용됐으며, **실제 출력에는 포함하지 않습니다**."
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


def _strip_code_fence(text: str) -> str:
    """Strip an outer ``` code fence an LLM may wrap the whole body in.

    Idempotent and safe on non-fenced text. Used defensively for the
    markdown summary path (Phase Z) so DB-stored summaries never carry a
    stray ``````markdown ... `````` wrapper even if the LLM disobeys the
    prompt rule.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    first_newline = stripped.find("\n")
    if first_newline == -1:
        return stripped
    body = stripped[first_newline + 1 :]

    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -len("```")]

    return body.strip()


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

    @staticmethod
    def _build_summary_system_prompt() -> str:
        """Static accessor for the session-compact system prompt.

        Exposed as a method to keep the surface discoverable and unit-testable
        without leaking the module-level constant.
        """
        return _SUMMARY_SYSTEM_PROMPT

    @staticmethod
    def _build_summary_user_prompt(
        prev_summary: str | None,
        messages: list[dict[str, str]],
    ) -> str:
        """Render the per-call user prompt for session compaction.

        Args:
            prev_summary: Previously stored session summary, or None/blank.
            messages: Chronologically ordered turns (already pollution-filtered).

        Returns:
            Rendered user prompt following PLAN.md Z-7 template.
        """
        prev = prev_summary.strip() if prev_summary else ""
        prev_block = prev or "(없음)"

        rendered_lines: list[str] = []
        for turn in messages:
            role = turn.get("role", "").lower()
            content = turn.get("content", "").strip()
            label = "USER" if role == "user" else "ASSISTANT"
            rendered_lines.append(f"- {label}: {content}")
        log_block = "\n".join(rendered_lines) if rendered_lines else "(없음)"

        return (
            "[이전 요약]\n"
            f"{prev_block}\n\n"
            "[새 대화 로그]\n"
            f"{log_block}\n\n"
            "[지시]\n"
            "위 Rule 을 지키며 통합 요약문을 작성하세요."
        )

    async def summarize_messages(
        self,
        messages: list[dict[str, str]],
        prev_summary: str | None = None,
    ) -> SummaryResult:
        """Compact a session's chat history into a short medical-context summary.

        Callers are responsible for pollution filtering; this method trusts
        the incoming message list and only enforces a minimal sanity check
        (at least two turns to avoid wasting an LLM call).

        Args:
            messages: Chronologically ordered, already-filtered turns.
            prev_summary: Previously stored session summary. When present,
                the LLM merges it with the new log instead of replacing.

        Returns:
            SummaryResult. ``status`` is OK when the LLM produced a usable
            summary, EMPTY when there is nothing worth summarizing, and
            FALLBACK on technical failure so callers keep the prior summary.
        """
        if len(messages) < 2:
            return SummaryResult(status=SummaryStatus.EMPTY, summary="", consumed_message_count=0, token_usage=None)

        if self.client is None:
            logger.error("[COMPACT] api_error type=NoClient; fallback to prior summary")
            return SummaryResult(status=SummaryStatus.FALLBACK, summary="", consumed_message_count=0, token_usage=None)

        user_prompt = self._build_summary_user_prompt(prev_summary=prev_summary, messages=messages)

        start = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=400,
            )
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "[COMPACT] api_error type=%s msg=%s after %dms; fallback to prior summary",
                type(e).__name__,
                _sanitize_error(str(e)),
                elapsed_ms,
            )
            return SummaryResult(status=SummaryStatus.FALLBACK, summary="", consumed_message_count=0, token_usage=None)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        raw = response.choices[0].message.content or ""
        cleaned = _strip_code_fence(_strip_wrapping(raw))

        token_usage: TokenUsage | None = None
        if response.usage is not None:
            token_usage = TokenUsage(
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        if not cleaned:
            logger.warning("[COMPACT] empty response after %dms; fallback to prior summary", elapsed_ms)
            return SummaryResult(
                status=SummaryStatus.FALLBACK,
                summary="",
                consumed_message_count=0,
                token_usage=token_usage,
            )

        logger.info(
            "[COMPACT] ok chars=%d msgs=%d tokens=%s took=%dms",
            len(cleaned),
            len(messages),
            _fmt_tokens(token_usage),
            elapsed_ms,
        )
        return SummaryResult(
            status=SummaryStatus.OK,
            summary=cleaned,
            consumed_message_count=len(messages),
            token_usage=token_usage,
        )

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
