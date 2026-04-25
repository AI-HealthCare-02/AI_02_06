"""Tool-calling RQ jobs — Phase Y.

두 가지 RQ task:
- ``route_intent_job(messages)`` — Router LLM 호출 → assistant message dict
- ``run_tool_calls_job(calls)``  — 한 턴의 모든 tool_calls 를 ``asyncio.gather``
  로 병행 실행, ``{tool_call_id: result}`` 반환

import 는 모듈 상단에 둔다. 실제 호출은 runtime monkeypatch 가능하도록
모듈 attribute 로 노출되므로 테스트는
``monkeypatch.setattr(jobs, "search_hospitals_by_keyword", ...)`` 로 대체 가능.
"""

import asyncio
import logging
from typing import Any

from ai_worker.domains.tool_calling import router_llm as router_provider
from app.dtos.tools import KakaoPlace
from app.services.tools.maps.hospital_search import (
    DEFAULT_RADIUS_M,
    HospitalCategory,
    search_hospitals_by_keyword,
    search_hospitals_by_location,
)

logger = logging.getLogger(__name__)

_CATEGORY_TO_ENUM: dict[str, HospitalCategory] = {
    "약국": HospitalCategory.PHARMACY,
    "병원": HospitalCategory.HOSPITAL,
}


async def route_intent_job(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """[RQ Task] Router LLM 호출 결과를 assistant message dict 로 반환.

    Args:
        messages: 시간순 대화 이력 (마지막은 사용자 turn).

    Returns:
        ``parse_router_response`` 입력으로 바로 사용 가능한 dict.
    """
    logger.info("[ToolCalling] route_intent_job start messages=%d", len(messages))
    result = await router_provider.route_with_tools(messages)
    _log_route_summary(result)
    return result


def _log_route_summary(result: dict[str, Any]) -> None:
    """Router 결과의 tool_calls 이름들을 한 줄 로그로 출력."""
    tool_calls = result.get("tool_calls") or []
    names_suffix = (
        " names=" + ",".join(c.get("function", {}).get("name", "?") for c in tool_calls) if tool_calls else ""
    )
    logger.info("[ToolCalling] route_intent_job done tool_calls=%d%s", len(tool_calls), names_suffix)


async def run_tool_calls_job(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """[RQ Task] 모든 tool_call 을 병행 실행해 ``{tool_call_id: result}`` 반환.

    Args:
        calls: 각 dict 가 ``tool_call_id``, ``name``, ``arguments`` 보유.
            location 호출은 ``geolocation: {lat, lng}`` 도 필요.

    Returns:
        성공 결과는 ``{"places": [...]}``, 실패는 ``{"error": str}``.
    """
    if not calls:
        return {}

    _log_run_start(calls)
    results = await asyncio.gather(*[_dispatch(call) for call in calls], return_exceptions=False)
    merged = {call["tool_call_id"]: result for call, result in zip(calls, results, strict=True)}
    _log_run_done(merged)
    return merged


def _log_run_start(calls: list[dict[str, Any]]) -> None:
    """병렬 호출 시작 로그."""
    logger.info(
        "[ToolCalling] run_tool_calls_job start calls=%d names=%s",
        len(calls),
        ",".join(c.get("name", "?") for c in calls),
    )


def _log_run_done(merged: dict[str, dict[str, Any]]) -> None:
    """병렬 호출 종료 로그 (성공/실패 카운트)."""
    error_count = sum(1 for r in merged.values() if "error" in r)
    logger.info("[ToolCalling] run_tool_calls_job done ok=%d errors=%d", len(merged) - error_count, error_count)


async def _dispatch(call: dict[str, Any]) -> dict[str, Any]:
    """단일 call dict 를 적절한 함수로 라우팅. 예외는 결과 dict 로 직렬화."""
    name = call.get("name", "")
    try:
        if name == "search_hospitals_by_keyword":
            return await _run_keyword(call)
        if name == "search_hospitals_by_location":
            return await _run_location(call)
    except Exception as exc:
        logger.exception("[ToolCalling] tool call %r failed", name)
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"error": f"unknown function: {name}"}


async def _run_keyword(call: dict[str, Any]) -> dict[str, Any]:
    """키워드 기반 병원/약국 검색을 실행한다."""
    arguments = call.get("arguments") or {}
    query = arguments.get("query", "")
    places = await search_hospitals_by_keyword(query=query)
    return {"places": _places_to_dict_list(places)}


async def _run_location(call: dict[str, Any]) -> dict[str, Any]:
    """위치 기반 병원/약국 검색을 실행한다 (geolocation 필수)."""
    geolocation = call.get("geolocation")
    if not _is_valid_geolocation(geolocation):
        return {"error": "missing geolocation: location tool requires lat/lng in call payload"}

    arguments = call.get("arguments") or {}
    category = _CATEGORY_TO_ENUM.get(arguments.get("category", "약국"), HospitalCategory.PHARMACY)
    radius_m = int(arguments.get("radius_m", DEFAULT_RADIUS_M))
    places = await search_hospitals_by_location(
        lat=float(geolocation["lat"]),
        lng=float(geolocation["lng"]),
        radius_m=radius_m,
        category=category,
    )
    return {"places": _places_to_dict_list(places)}


def _is_valid_geolocation(geolocation: dict[str, Any] | None) -> bool:
    """Geolocation dict 가 lat/lng 를 모두 가졌는지 확인."""
    return bool(geolocation) and "lat" in geolocation and "lng" in geolocation


def _places_to_dict_list(places: list[KakaoPlace]) -> list[dict[str, Any]]:
    """KakaoPlace 리스트를 RQ pickle 안전한 dict 리스트로 변환."""
    return [p.model_dump() for p in places]
