"""Tool calling RQ jobs (AI-Worker only).

Phase Y 의 두 신규 RQ job. 모두 RQ 2.x native async 규약 (``async def``
+ pickle-safe primitives in/out).

- ``route_intent_job(messages)``  — Router LLM 호출 → assistant message dict
- ``run_tool_calls_job(calls)``   — 한 턴의 모든 tool_calls 를 ``asyncio.gather``
                                    로 병행 실행, ``{tool_call_id: result}`` 반환

import 는 모듈 상단에 둔다 (프로젝트 정책: top-level only). 실제 호출은
runtime 에 monkeypatch 가능하도록 모듈 attribute 로 노출되므로 테스트는
``monkeypatch.setattr(tool_tasks, "search_hospitals_by_keyword", ...)`` 로
대체할 수 있다.
"""

import asyncio
import logging
from typing import Any

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


# ── Router LLM ─────────────────────────────────────────────────


async def route_intent_job(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the Router LLM and return the assistant message dict.

    Args:
        messages: Chronological chat history including the latest user turn.

    Returns:
        ``{"role": "assistant", "content": ..., "tool_calls": ...}`` —
        직접 ``parse_router_response`` 입력으로 사용 가능.
    """
    from ai_worker.providers import router as router_provider

    logger.info("[ToolCalling] route_intent_job start messages=%d", len(messages))
    result = await router_provider.route_with_tools(messages)
    tool_calls = result.get("tool_calls") or []
    logger.info(
        "[ToolCalling] route_intent_job done tool_calls=%d%s",
        len(tool_calls),
        " names=" + ",".join(c.get("function", {}).get("name", "?") for c in tool_calls) if tool_calls else "",
    )
    return result


# ── Tool 병렬 실행 ─────────────────────────────────────────────


def _places_to_dict_list(places: list[KakaoPlace]) -> list[dict[str, Any]]:
    """KakaoPlace 리스트를 RQ pickle 안전한 dict 리스트로."""
    return [p.model_dump() for p in places]


async def _run_keyword(call: dict[str, Any]) -> dict[str, Any]:
    arguments = call.get("arguments") or {}
    query = arguments.get("query", "")
    places = await search_hospitals_by_keyword(query=query)
    return {"places": _places_to_dict_list(places)}


async def _run_location(call: dict[str, Any]) -> dict[str, Any]:
    geolocation = call.get("geolocation")
    if not geolocation or "lat" not in geolocation or "lng" not in geolocation:
        return {"error": "missing geolocation: location tool requires lat/lng in call payload"}

    arguments = call.get("arguments") or {}
    category_label = arguments.get("category", "약국")
    category = _CATEGORY_TO_ENUM.get(category_label, HospitalCategory.PHARMACY)
    radius_m = int(arguments.get("radius_m", DEFAULT_RADIUS_M))

    places = await search_hospitals_by_location(
        lat=float(geolocation["lat"]),
        lng=float(geolocation["lng"]),
        radius_m=radius_m,
        category=category,
    )
    return {"places": _places_to_dict_list(places)}


async def _dispatch(call: dict[str, Any]) -> dict[str, Any]:
    """Route a single call dict to its function. Errors are caught + serialized."""
    name = call.get("name", "")
    try:
        if name == "search_hospitals_by_keyword":
            return await _run_keyword(call)
        if name == "search_hospitals_by_location":
            return await _run_location(call)
    except Exception as exc:  # 병렬 호출 격리 — 실패도 결과로 전달
        logger.exception("[ToolCalling] tool call %r failed", name)
        return {"error": f"{type(exc).__name__}: {exc}"}
    else:
        return {"error": f"unknown function: {name}"}


async def run_tool_calls_job(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Execute every tool call in ``calls`` concurrently.

    Args:
        calls: List of dicts. Each dict has at minimum ``tool_call_id``,
            ``name``, ``arguments``. Location calls additionally need
            ``geolocation: {lat, lng}`` injected by the caller (FastAPI
            side, after the GPS callback arrives).

    Returns:
        Dict keyed by ``tool_call_id`` with each call's result. Successful
        results carry ``{"places": [...]}``; failures carry ``{"error": str}``.
    """
    if not calls:
        return {}

    logger.info(
        "[ToolCalling] run_tool_calls_job start calls=%d names=%s",
        len(calls),
        ",".join(c.get("name", "?") for c in calls),
    )
    coros = [_dispatch(call) for call in calls]
    results = await asyncio.gather(*coros, return_exceptions=False)

    merged = {call["tool_call_id"]: result for call, result in zip(calls, results, strict=True)}
    error_count = sum(1 for r in merged.values() if "error" in r)
    logger.info("[ToolCalling] run_tool_calls_job done ok=%d errors=%d", len(merged) - error_count, error_count)
    return merged
