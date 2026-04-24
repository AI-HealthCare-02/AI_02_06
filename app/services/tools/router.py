"""Router LLM 응답 파서 + 분기 헬퍼.

본 모듈은 OpenAI 호출을 직접 하지 않는다. 그 호출은 AI-Worker 의 RQ
job 안에서 일어나고 (Y-5), 본 모듈은 그 결과 (assistant message dict)
를 ``RouteResult`` 도메인 DTO 로 변환하는 순수 함수만 노출한다.

이렇게 분리하는 이유:
1. RQ job 의 출력은 pickle 안전한 dict 여야 한다 → ``RouteResult`` 자체는
   FastAPI 측에서 ``model_validate`` 로 복원.
2. parse 로직은 OpenAI client 의존성 없이 단위 테스트 가능.
3. Router 호출 정책 (parallel_tool_calls=True 등) 은 Y-5 한 곳에 묶여있고,
   해석은 본 모듈에서 일관 관리.
"""

import json
import logging
from typing import Any

from app.dtos.tools import RouteResult, ToolCall

logger = logging.getLogger(__name__)

_LOCATION_TOOL_NAMES = frozenset({"search_hospitals_by_location"})


def needs_geolocation_for(name: str, arguments: dict[str, Any]) -> bool:
    """함수 이름·인자 조합으로 GPS 콜백이 필요한지 판단.

    현 단계에서는 ``search_hospitals_by_location`` 만 좌표가 필요하다.
    이후 PendingTurn 분기에서 그대로 사용된다.

    Args:
        name: OpenAI tool function name.
        arguments: 파싱된 인자 dict (현재는 미사용, 미래 확장 자리).

    Returns:
        ``True`` 면 사용자 GPS 콜백 대기, ``False`` 면 즉시 실행 가능.
    """
    del arguments  # 미래 확장 슬롯
    return name in _LOCATION_TOOL_NAMES


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    """OpenAI 가 종종 잘리거나 깨진 JSON 을 줄 수 있어 안전 파싱."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("[ToolCalling] router JSON parse failed, falling back to empty args")
        return {}
    if not isinstance(parsed, dict):
        logger.warning("[ToolCalling] router arguments not a dict (type=%s), using empty args", type(parsed).__name__)
        return {}
    return parsed


def parse_router_response(message: dict[str, Any]) -> RouteResult:
    """Convert one OpenAI ``choices[0].message`` (as dict) into a ``RouteResult``.

    분기 규칙:
    - ``tool_calls`` 가 비어있거나 ``None`` → ``kind="text"``,
      ``content`` 를 ``text`` 에 담는다 (None 은 빈 문자열로 정규화).
    - ``tool_calls`` 가 한 개 이상 → ``kind="tool_calls"``, 각 호출을
      ``ToolCall`` 로 매핑하고 ``needs_geolocation`` 자동 산출.

    Args:
        message: OpenAI assistant message dict. Pydantic / dataclass 객체를
            받았다면 호출 측에서 ``model_dump()`` 등으로 dict 화 후 전달.

    Returns:
        ``RouteResult``. ``assistant_message`` 에 원본 dict 전체가 보존된다.
    """
    raw_calls = message.get("tool_calls") or []

    if not raw_calls:
        content = message.get("content") or ""
        return RouteResult(kind="text", text=content, assistant_message=message)

    parsed_calls: list[ToolCall] = []
    for raw_call in raw_calls:
        function = raw_call.get("function", {})
        name = function.get("name", "")
        arguments = _parse_arguments(function.get("arguments"))
        parsed_calls.append(
            ToolCall(
                tool_call_id=raw_call.get("id", ""),
                name=name,
                arguments=arguments,
                needs_geolocation=needs_geolocation_for(name, arguments),
            ),
        )

    return RouteResult(kind="tool_calls", tool_calls=parsed_calls, assistant_message=message)
