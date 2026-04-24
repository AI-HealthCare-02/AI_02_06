"""AI-Worker Router LLM provider.

Router LLM 호출은 RAG 의 ``RAGGenerator`` 와 인자 모양이 달라 (tools,
parallel_tool_calls, tool_choice) 별도 진입점으로 둔다. AsyncOpenAI
client 는 동일 프로세스 내 모듈 싱글톤으로 재사용한다.

본 모듈의 책임:
1. AsyncOpenAI ``chat.completions.create`` 를 ``tools`` 파라미터와 함께 호출.
2. 응답의 ``choices[0].message`` 를 dict 로 정규화 — RQ pickle 안전 + FastAPI
   측 ``parse_router_response`` 가 그대로 받을 수 있는 형태.

본 모듈은 ``RouteResult`` 를 만들지 않는다. 그 변환은 FastAPI 측에서
``parse_router_response`` 로 수행한다 (계층 책임 분리).
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import config
from app.services.tools.schemas import TOOL_SCHEMAS

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazily instantiate and reuse the AsyncOpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        logger.info("AsyncOpenAI client initialised for Router (model=%s)", _MODEL)
    return _client


def _serialize_tool_call(call: Any) -> dict[str, Any]:
    """Convert an OpenAI ChatCompletionMessageToolCall into a plain dict.

    Both real OpenAI v1 objects and MagicMock-based test doubles expose
    ``id`` / ``type`` / ``function.{name,arguments}`` attributes, so simple
    attribute access is enough.
    """
    function = call.function
    return {
        "id": call.id,
        "type": getattr(call, "type", "function"),
        "function": {"name": function.name, "arguments": function.arguments},
    }


async def route_with_tools(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Call the Router LLM and return the assistant message as a plain dict.

    Args:
        messages: Chronological chat turns ending with the latest user input.

    Returns:
        ``{"role": "assistant", "content": str | None, "tool_calls": list | None}``
        — same shape ``parse_router_response`` consumes.
    """
    client = _get_openai_client()

    completion = await client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        parallel_tool_calls=True,
    )

    message = completion.choices[0].message

    raw_tool_calls = getattr(message, "tool_calls", None)
    tool_calls_dict: list[dict[str, Any]] | None = (
        [_serialize_tool_call(c) for c in raw_tool_calls] if raw_tool_calls else None
    )

    usage = getattr(completion, "usage", None)
    total_tokens = getattr(usage, "total_tokens", None) if usage else None
    logger.info(
        "[ToolCalling] router LLM response tool_calls=%d tokens=%s",
        len(tool_calls_dict) if tool_calls_dict else 0,
        total_tokens if total_tokens is not None else "?",
    )

    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": tool_calls_dict,
    }
