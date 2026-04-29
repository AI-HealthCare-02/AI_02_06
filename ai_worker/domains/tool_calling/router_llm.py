"""Router LLM — Phase Y / 옵션 C 의 도구 호출 라우터.

OpenAI Chat Completion 을 ``tools`` + ``parallel_tool_calls=True`` 로 호출하고,
응답 메시지를 RQ pickle 안전한 dict 로 직렬화한다. RAG 의 응답 생성과는
인자 모양이 달라 별도 도메인 진입점으로 둔다.

본 모듈은 ``RouteResult`` 같은 도메인 DTO 를 만들지 않는다 — 그 변환은
FastAPI 측 ``parse_router_response`` 가 담당한다 (계층 책임 분리).

옵션 C 변경:
Router LLM 의 tool 선택이 **의도 분류** 의 단일 메커니즘 역할을 한다.
별도 IntentClassifier 가 폐기되므로 본 모듈의 ``ROUTER_SYSTEM_PROMPT`` 가
의학 도메인 → tool 강제 / 도메인 외 → 직접 거절 / referent 없는 대명사 →
직접 명확화 질문 의 분기 룰을 모두 짊어진다. system prompt 가 messages
앞에 자동 prepend 된다.
"""

import logging
from typing import Any

from openai.types.chat import ChatCompletion as OpenAIChatCompletion
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from ai_worker.core.openai_client import get_openai_client
from app.services.tools.schemas import TOOL_SCHEMAS

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"

ROUTER_SYSTEM_PROMPT = (
    "당신은 'Dayak' 약사 챗봇의 라우터입니다. "
    "사용자의 마지막 메시지를 보고 아래 분기 중 하나로 응답합니다.\n\n"
    "## 사용 가능한 도구\n"
    "- search_medicine_knowledge_base(query): 약 정보, 부작용, 복용법, 효능, "
    "성분, 상호작용 등 의학/약학 도메인 지식 검색\n"
    "- search_hospitals_by_keyword(query): 지명·랜드마크로 약국/병원 검색 "
    "('강남역 약국', '서울대병원')\n"
    "- search_hospitals_by_location(category, radius_m): 사용자 GPS 주변 "
    "약국/병원 검색 ('내 주변', '근처')\n\n"
    "## 분기 룰\n"
    "1. **의학/약학 도메인 질문** (약 이름·증상·부작용·복용법·성분·효능·"
    "상호작용·영양제 등)\n"
    "   → 반드시 search_medicine_knowledge_base 호출\n"
    "   → query 인자는 대화 이력의 대명사·생략 주어·지시어를 풀어 "
    "self-contained 한 한 문장으로 작성\n"
    '   → 예: 이전 턴 "타이레놀 알려줘" + 이번 턴 "그거 부작용은?" → '
    'query="타이레놀의 부작용"\n'
    '   → 예: "오메가3와 와파린 같이 먹어도 돼?" → '
    'query="오메가3와 와파린의 상호작용"\n\n'
    "2. **위치 기반 질문** (병원·약국 찾기)\n"
    "   → '근처/주변/내 주변' → search_hospitals_by_location\n"
    "   → '강남역 약국' 같은 지명 명시 → search_hospitals_by_keyword\n"
    "   → 두 의도가 섞이면 parallel_tool_calls 로 두 함수 동시 호출 가능\n\n"
    "3. **도메인 외 질문** (정치, 시사, 잡담, 인사, 욕설, 일반 상식, 날씨 등)\n"
    "   → tool 호출하지 않음\n"
    "   → 친절한 한국어로 직접 답변: "
    '"저는 약 정보와 병원/약국 검색을 도와드리는 챗봇이에요. '
    '약 복용법, 부작용, 영양제, 근처 약국 같은 질문을 해주세요."\n\n'
    "4. **대명사가 있는데 history 에서 referent 를 찾을 수 없는 질문**\n"
    "   → tool 호출하지 않음\n"
    "   → 친절하게 어떤 약·증상에 대한 질문인지 되물음: "
    '"어느 약에 대한 질문인지 약 이름을 알려주세요."\n\n'
    "## 절대 규칙\n"
    "- 의학 도메인이면 직접 답변하지 말고 반드시 tool 을 호출하라.\n"
    "- 도메인 외 또는 referent 없는 대명사이면 tool 을 절대 호출하지 말고 "
    "직접 답변하라.\n"
    '- query 인자에 대명사·"그거"·"이거" 같은 미해결 지시어를 절대 남기지 마라.\n'
)


async def route_with_tools(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Router LLM 을 호출해 assistant 메시지 dict 를 반환한다.

    호출 측이 넘긴 ``messages`` 앞에 ``ROUTER_SYSTEM_PROMPT`` 를 system role 로
    prepend 한다 — 호출 측은 system prompt 를 신경쓰지 않고 사용자 history 만
    실어 보내면 된다.

    Args:
        messages: 시간순 대화 턴 (마지막은 사용자 입력). system role 메시지를
            포함시키지 말 것 — 본 함수가 자동 추가한다.

    Returns:
        ``{"role": "assistant", "content": str | None, "tool_calls": list | None}``.
    """
    client = get_openai_client()
    if client is None:
        logger.error("[ToolCalling] router LLM unavailable (no OpenAI client)")
        return {"role": "assistant", "content": None, "tool_calls": None}

    full_messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}, *messages]
    completion = await client.chat.completions.create(
        model=_MODEL,
        messages=full_messages,
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
