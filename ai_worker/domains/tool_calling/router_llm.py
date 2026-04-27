"""Router LLM — Phase Y 의 도구 호출 라우터.

OpenAI Chat Completion 을 ``tools`` + ``parallel_tool_calls=True`` 로 호출하고,
응답 메시지를 RQ pickle 안전한 dict 로 직렬화한다. RAG 의 응답 생성과는
인자 모양이 달라 별도 도메인 진입점으로 둔다.

본 모듈은 ``RouteResult`` 같은 도메인 DTO 를 만들지 않는다 — 그 변환은
FastAPI 측 ``parse_router_response`` 가 담당한다 (계층 책임 분리).
"""

import logging
from typing import Any

from openai.types.chat import ChatCompletion as OpenAIChatCompletion
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from ai_worker.core.openai_client import get_openai_client
from app.services.tools.schemas import TOOL_SCHEMAS

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"


async def route_with_tools(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Router LLM 을 호출해 assistant 메시지 dict 를 반환한다.

    Args:
        messages: 시간순 대화 턴 (마지막은 사용자 입력).

    Returns:
        ``{"role": "assistant", "content": str | None, "tool_calls": list | None}``.
    """
    client = get_openai_client()
    if client is None:
        logger.error("[ToolCalling] router LLM unavailable (no OpenAI client)")
        return {"role": "assistant", "content": None, "tool_calls": None}

    completion = await client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        parallel_tool_calls=True,
    )
    return _to_assistant_dict(completion)


def _to_assistant_dict(completion: OpenAIChatCompletion) -> dict[str, Any]:
    """Completion 을 assistant message dict 로 변환 + 로깅."""
    message = completion.choices[0].message
    tool_calls_dict = _serialize_tool_calls(getattr(message, "tool_calls", None))
    _log_router_response(completion, tool_calls_dict)
    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": tool_calls_dict,
    }


def _serialize_tool_calls(
    raw_tool_calls: list[ChatCompletionMessageToolCall] | None,
) -> list[dict[str, Any]] | None:
    """OpenAI tool_call 객체 리스트 → plain dict 리스트."""
    if not raw_tool_calls:
        return None
    return [_serialize_tool_call(call) for call in raw_tool_calls]


def _serialize_tool_call(call: Any) -> dict[str, Any]:
    """단일 ChatCompletionMessageToolCall → dict (실제/Mock 모두 지원)."""
    function = call.function
    return {
        "id": call.id,
        "type": getattr(call, "type", "function"),
        "function": {"name": function.name, "arguments": function.arguments},
    }


def _log_router_response(
    completion: OpenAIChatCompletion,
    tool_calls_dict: list[dict[str, Any]] | None,
) -> None:
    """Router 응답 결과를 한 줄 로그로 남긴다."""
    usage = getattr(completion, "usage", None)
    total_tokens = getattr(usage, "total_tokens", None) if usage else None
    logger.info(
        "[ToolCalling] router LLM response tool_calls=%d tokens=%s",
        len(tool_calls_dict) if tool_calls_dict else 0,
        total_tokens if total_tokens is not None else "?",
    )
