"""LLM Router schemas + 응답 파서 계약 테스트 (Y-4 Red).

Router LLM 의 OpenAI 호출 자체는 Y-5 의 AI-Worker RQ job 에서 일어난다.
본 테스트는 Y-4 가 책임지는 두 가지만 검증한다:

1. ``app/services/tools/schemas.py`` — 두 함수의 OpenAI tools 스펙이
   parallel_tool_calls + tool_choice="auto" 호출에 그대로 넣을 수 있는
   포맷을 따르는가.
2. ``app/services/tools/router.py::parse_router_response`` — OpenAI
   ChatCompletion 응답(또는 그것을 dict 로 흉내낸 객체)을 받아
   ``RouteResult`` 로 변환한다.

Red 전제:
- ``HOSPITAL_LOCATION_TOOL``, ``HOSPITAL_KEYWORD_TOOL`` 모듈 상수
- ``TOOL_SCHEMAS`` 리스트 (Router 호출용)
- ``RouteResult`` Pydantic DTO with ``kind: Literal["text", "tool_calls"]``
- ``parse_router_response(message_dict) -> RouteResult``
- ``needs_geolocation_for(name, arguments) -> bool``
"""

import json

from app.dtos.tools import RouteResult
from app.services.tools.router import (
    needs_geolocation_for,
    parse_router_response,
)
from app.services.tools.schemas import (
    HOSPITAL_KEYWORD_TOOL,
    HOSPITAL_LOCATION_TOOL,
    TOOL_SCHEMAS,
)

# ── OpenAI tools 스펙 ─────────────────────────────────────────


class TestHospitalLocationToolSchema:
    def test_function_name_matches_codebase(self) -> None:
        assert HOSPITAL_LOCATION_TOOL["function"]["name"] == "search_hospitals_by_location"

    def test_type_is_function(self) -> None:
        assert HOSPITAL_LOCATION_TOOL["type"] == "function"

    def test_has_description_in_korean(self) -> None:
        desc = HOSPITAL_LOCATION_TOOL["function"]["description"]
        assert isinstance(desc, str)
        assert desc

    def test_parameters_define_category_and_radius(self) -> None:
        props = HOSPITAL_LOCATION_TOOL["function"]["parameters"]["properties"]
        assert "category" in props
        assert "radius_m" in props
        # category 는 약국/병원 enum
        assert set(props["category"]["enum"]) == {"약국", "병원"}

    def test_required_includes_category(self) -> None:
        required = HOSPITAL_LOCATION_TOOL["function"]["parameters"]["required"]
        assert "category" in required


class TestHospitalKeywordToolSchema:
    def test_function_name_matches_codebase(self) -> None:
        assert HOSPITAL_KEYWORD_TOOL["function"]["name"] == "search_hospitals_by_keyword"

    def test_parameters_define_query(self) -> None:
        props = HOSPITAL_KEYWORD_TOOL["function"]["parameters"]["properties"]
        assert "query" in props

    def test_required_includes_query(self) -> None:
        required = HOSPITAL_KEYWORD_TOOL["function"]["parameters"]["required"]
        assert "query" in required


class TestToolSchemasList:
    def test_contains_both_tools(self) -> None:
        names = {t["function"]["name"] for t in TOOL_SCHEMAS}
        assert names == {"search_hospitals_by_location", "search_hospitals_by_keyword"}


# ── needs_geolocation_for ──────────────────────────────────────


class TestNeedsGeolocationFor:
    def test_location_tool_needs_geolocation(self) -> None:
        assert needs_geolocation_for("search_hospitals_by_location", {"category": "약국"}) is True

    def test_keyword_tool_does_not_need_geolocation(self) -> None:
        assert needs_geolocation_for("search_hospitals_by_keyword", {"query": "강남역 약국"}) is False

    def test_unknown_tool_does_not_need_geolocation(self) -> None:
        assert needs_geolocation_for("foo_bar", {}) is False


# ── parse_router_response (text 케이스) ────────────────────────


class TestParseRouterResponseText:
    def test_assistant_text_only_yields_text_route(self) -> None:
        message = {"role": "assistant", "content": "안녕하세요!", "tool_calls": None}
        result = parse_router_response(message)

        assert isinstance(result, RouteResult)
        assert result.kind == "text"
        assert result.text == "안녕하세요!"
        assert result.tool_calls == []

    def test_empty_content_and_no_tool_calls_yields_empty_text(self) -> None:
        message = {"role": "assistant", "content": "", "tool_calls": None}
        result = parse_router_response(message)

        assert result.kind == "text"
        assert result.text == ""

    def test_none_content_normalized_to_empty_string(self) -> None:
        message = {"role": "assistant", "content": None, "tool_calls": None}
        result = parse_router_response(message)

        assert result.kind == "text"
        assert result.text == ""


# ── parse_router_response (tool_calls 케이스) ──────────────────


class TestParseRouterResponseToolCalls:
    def test_single_keyword_tool_call(self) -> None:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_keyword",
                        "arguments": json.dumps({"query": "강남역 약국"}),
                    },
                }
            ],
        }
        result = parse_router_response(message)

        assert result.kind == "tool_calls"
        assert len(result.tool_calls) == 1

        call = result.tool_calls[0]
        assert call.tool_call_id == "call_abc"
        assert call.name == "search_hospitals_by_keyword"
        assert call.arguments == {"query": "강남역 약국"}
        assert call.needs_geolocation is False

    def test_single_location_tool_call_marks_needs_geolocation(self) -> None:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_loc",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_location",
                        "arguments": json.dumps({"category": "약국", "radius_m": 1500}),
                    },
                }
            ],
        }
        result = parse_router_response(message)

        assert result.kind == "tool_calls"
        call = result.tool_calls[0]
        assert call.needs_geolocation is True
        assert call.arguments["category"] == "약국"
        assert call.arguments["radius_m"] == 1500

    def test_multiple_tool_calls_preserve_order(self) -> None:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_keyword",
                        "arguments": json.dumps({"query": "강남역 약국"}),
                    },
                },
                {
                    "id": "c2",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_location",
                        "arguments": json.dumps({"category": "병원"}),
                    },
                },
            ],
        }
        result = parse_router_response(message)

        assert result.kind == "tool_calls"
        assert [c.tool_call_id for c in result.tool_calls] == ["c1", "c2"]
        assert result.tool_calls[0].needs_geolocation is False
        assert result.tool_calls[1].needs_geolocation is True

    def test_assistant_message_preserved_in_result(self) -> None:
        """병렬 호출 후 2nd LLM 호출에 assistant message 전체를 다시 넣어야 하므로 보존."""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_keyword",
                        "arguments": json.dumps({"query": "역삼동 약국"}),
                    },
                },
            ],
        }
        result = parse_router_response(message)

        assert result.assistant_message == message


class TestParseRouterResponseEdgeCases:
    def test_malformed_arguments_yields_empty_dict(self) -> None:
        """OpenAI 가 종종 잘리거나 깨진 JSON 을 줄 수 있다 — 빈 dict 로 안전 처리."""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "search_hospitals_by_keyword",
                        "arguments": "{not json",
                    },
                },
            ],
        }
        result = parse_router_response(message)

        assert result.kind == "tool_calls"
        assert result.tool_calls[0].arguments == {}

    def test_tool_calls_empty_list_yields_text_kind(self) -> None:
        message = {"role": "assistant", "content": "직접 답변", "tool_calls": []}
        result = parse_router_response(message)

        assert result.kind == "text"
        assert result.text == "직접 답변"
