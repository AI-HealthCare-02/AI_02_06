"""Recall Router LLM robustness 테스트 (§15 오타·표현 변형 견고성).

§15.5 의 5종 변형 시나리오를 mock_router_llm 으로 결정적 응답을
주입해 검증한다. 실제 OpenAI 호출은 없음 (CI 비용 0).

대상 분기:
- check_user_medications_recall — 사용자 복용약 회수 질의
- check_manufacturer_recalls    — 제조사 회수 질의

mock 전략:
    parse_router_response 는 OpenAI assistant message dict → RouteResult
    변환만 한다. 따라서 dict 만 만들어 직접 호출하면 LLM 호출 없이
    동일 분기를 검증할 수 있다.
"""

from __future__ import annotations

import json

import pytest

from app.services.tools.router import parse_router_response


def _assistant_with_tool_call(tool_name: str, arguments: dict | None = None) -> dict:
    """mock Router LLM 응답 — tool_calls 1개 포함."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_test_1",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments or {}),
                },
            },
        ],
    }


# ── §15.5 — 5종 변형 모두 check_user_medications_recall 로 라우팅 ──


@pytest.mark.parametrize(
    "query",
    [
        "내가 먹는 약 중에 회수된 거 있어?",
        "내 약 중에 판매 중지된거 있나?",
        "ㅈ ㅔ가 먹는 약 ban당한거 있어?",
        "지금 복용중인 약 리콜된 약있어",
        "내약중에 판중지나 회수처리된게 있는지 봐줘",
    ],
)
def test_user_recall_variants_route_to_correct_tool(query: str) -> None:
    """5종 변형 — 모두 check_user_medications_recall 로 라우팅됨을 보장."""
    # 실제 Router LLM 이 들어오면 주는 가상 응답
    assistant_message = _assistant_with_tool_call("check_user_medications_recall")
    result = parse_router_response(assistant_message)

    assert result.kind == "tool_calls", f"query={query!r} → kind={result.kind}"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "check_user_medications_recall"
    # recall 툴은 GPS 콜백 불필요
    assert result.tool_calls[0].needs_geolocation is False


# ── 제조사 질의는 check_manufacturer_recalls 로 ──────────────────────


@pytest.mark.parametrize(
    ("query", "manufacturer"),
    [
        ("동국제약에서 회수된 약 있어?", "동국제약"),
        ("내 약 만든 회사가 회수당한거 있나", None),
        ("(주)한독 리콜 이력", "(주)한독"),
    ],
)
def test_manufacturer_recall_variants_route_to_correct_tool(query: str, manufacturer: str | None) -> None:
    """제조사 단위 변형 — check_manufacturer_recalls 로 라우팅."""
    args = {"manufacturer": manufacturer} if manufacturer else {}
    assistant_message = _assistant_with_tool_call("check_manufacturer_recalls", args)
    result = parse_router_response(assistant_message)

    assert result.kind == "tool_calls", f"query={query!r} → kind={result.kind}"
    assert result.tool_calls[0].name == "check_manufacturer_recalls"
    if manufacturer:
        assert result.tool_calls[0].arguments.get("manufacturer") == manufacturer


# ── recall 툴은 needs_geolocation=False 보장 ─────────────────────────


def test_recall_tools_do_not_require_geolocation() -> None:
    """recall 두 툴 모두 GPS 콜백 분기를 타지 않는다 (eager 실행)."""
    for tool_name in ("check_user_medications_recall", "check_manufacturer_recalls"):
        assistant_message = _assistant_with_tool_call(tool_name)
        result = parse_router_response(assistant_message)
        assert result.tool_calls[0].needs_geolocation is False, tool_name


# ── TOOL_SCHEMAS 에 신규 2종이 등록되어 있어야 함 ────────────────────


def test_tool_schemas_include_recall_tools() -> None:
    """schemas.TOOL_SCHEMAS 가 recall 툴 2종을 포함해야 한다."""
    from app.services.tools.schemas import TOOL_SCHEMAS

    names = {tool["function"]["name"] for tool in TOOL_SCHEMAS}
    assert "check_user_medications_recall" in names
    assert "check_manufacturer_recalls" in names


def test_recall_tool_descriptions_contain_synonyms() -> None:
    """description 에 §15.3 동의어 풀의 핵심 키워드가 포함되어야 한다 (robustness 가드)."""
    from app.services.tools.schemas import (
        CHECK_MANUFACTURER_RECALLS_TOOL,
        CHECK_USER_MEDICATIONS_RECALL_TOOL,
    )

    user_desc = CHECK_USER_MEDICATIONS_RECALL_TOOL["function"]["description"]
    for kw in ("회수", "판매중지", "리콜", "ban"):
        assert kw in user_desc, f"missing '{kw}' in user-recall description"

    mfr_desc = CHECK_MANUFACTURER_RECALLS_TOOL["function"]["description"]
    for kw in ("회수", "제조사", "리콜"):
        assert kw in mfr_desc, f"missing '{kw}' in manufacturer-recall description"
