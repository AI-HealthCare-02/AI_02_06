"""AI-Worker tool RQ job 계약 테스트 (Y-5 Red).

Phase Y 의 두 신규 job:

- ``route_intent_job(messages)`` — Router LLM 호출 → ``RouteResult`` dict
- ``run_tool_calls_job(calls)`` — 병렬 hospital_search 실행 → 결과 dict

두 job 모두 RQ 2.x native async 규약을 따라야 하며, 입출력은 RQ pickle
경로를 안전히 통과할 수 있도록 기본 타입(dict/list/str/...) 만 사용한다.

본 테스트는 시그니처와 분기 동작을 검증하고, 실제 OpenAI/카카오 호출은
``monkeypatch`` 로 가짜 함수에 위임한다.
"""

import inspect
from typing import Any

import pytest

from ai_worker.domains.tool_calling import jobs as tool_tasks
from app.dtos.tools import KakaoPlace

# ── 시그니처 ────────────────────────────────────────────────────


class TestModuleExports:
    def test_route_intent_job_exported(self) -> None:
        assert hasattr(tool_tasks, "route_intent_job")

    def test_run_tool_calls_job_exported(self) -> None:
        assert hasattr(tool_tasks, "run_tool_calls_job")


class TestRouteIntentJobSignature:
    def test_is_async(self) -> None:
        assert inspect.iscoroutinefunction(tool_tasks.route_intent_job)

    def test_signature_has_messages(self) -> None:
        sig = inspect.signature(tool_tasks.route_intent_job)
        assert "messages" in sig.parameters


class TestRunToolCallsJobSignature:
    def test_is_async(self) -> None:
        assert inspect.iscoroutinefunction(tool_tasks.run_tool_calls_job)

    def test_signature_has_calls(self) -> None:
        sig = inspect.signature(tool_tasks.run_tool_calls_job)
        assert "calls" in sig.parameters


# ── route_intent_job 위임 ──────────────────────────────────────


class TestRouteIntentJobDelegatesToProvider:
    @pytest.mark.asyncio
    async def test_delegates_to_router_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        expected = {"kind": "text", "text": "안녕하세요!", "tool_calls": [], "assistant_message": None}

        async def fake_route(messages: list[dict]) -> dict:
            captured["messages"] = messages
            return expected

        from ai_worker.domains.tool_calling import router_llm as router_provider

        monkeypatch.setattr(router_provider, "route_with_tools", fake_route)

        msgs = [{"role": "user", "content": "안녕"}]
        result = await tool_tasks.route_intent_job(messages=msgs)

        assert captured["messages"] == msgs
        assert result == expected


# ── run_tool_calls_job 병렬 실행 ───────────────────────────────


def _place(name: str, place_id: str = "1") -> KakaoPlace:
    return KakaoPlace(
        id=place_id,
        place_name=name,
        address="서울 어딘가",
        road_address=None,
        phone=None,
        category_name=None,
        category_group_code="PM9",
        lat=37.5,
        lng=127.0,
    )


class TestRunToolCallsJobKeyword:
    @pytest.mark.asyncio
    async def test_keyword_call_invokes_search_by_keyword(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        async def fake_kw(*, query: str) -> list[KakaoPlace]:
            captured["query"] = query
            return [_place("강남스퀘어약국")]

        async def fake_loc(**_: Any) -> list[KakaoPlace]:
            raise AssertionError("location 함수가 호출되면 안 됨")

        from ai_worker.domains.tool_calling import jobs as tt

        monkeypatch.setattr(tt, "search_hospitals_by_keyword", fake_kw)
        monkeypatch.setattr(tt, "search_hospitals_by_location", fake_loc)

        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_keyword",
                    "arguments": {"query": "강남역 약국"},
                },
            ],
        )

        assert captured["query"] == "강남역 약국"
        assert "c1" in result
        assert isinstance(result["c1"], dict)
        assert result["c1"]["places"][0]["place_name"] == "강남스퀘어약국"


class TestRunToolCallsJobLocation:
    @pytest.mark.asyncio
    async def test_location_call_passes_lat_lng_radius_category(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        async def fake_loc(*, lat: float, lng: float, radius_m: int, category) -> list[KakaoPlace]:
            captured.update(lat=lat, lng=lng, radius_m=radius_m, category=category)
            return [_place("미진약국")]

        from ai_worker.domains.tool_calling import jobs as tt

        monkeypatch.setattr(tt, "search_hospitals_by_location", fake_loc)

        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_location",
                    "arguments": {"category": "약국", "radius_m": 1500},
                    "geolocation": {"lat": 37.4978, "lng": 127.0286},
                },
            ],
        )

        assert captured["lat"] == 37.4978
        assert captured["lng"] == 127.0286
        assert captured["radius_m"] == 1500
        # category 는 HospitalCategory.PHARMACY (StrEnum) 으로 변환되어야 함
        assert str(captured["category"]) == "PM9"
        assert result["c1"]["places"][0]["place_name"] == "미진약국"

    @pytest.mark.asyncio
    async def test_hospital_category_translates_to_hp8(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        async def fake_loc(*, lat: float, lng: float, radius_m: int, category) -> list[KakaoPlace]:
            del lat, lng, radius_m  # 시그니처 유지용
            captured["category"] = category
            return []

        from ai_worker.domains.tool_calling import jobs as tt

        monkeypatch.setattr(tt, "search_hospitals_by_location", fake_loc)

        await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_location",
                    "arguments": {"category": "병원"},
                    "geolocation": {"lat": 37.5, "lng": 127.0},
                },
            ],
        )

        assert str(captured["category"]) == "HP8"


class TestRunToolCallsJobParallel:
    @pytest.mark.asyncio
    async def test_two_calls_run_in_parallel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """asyncio.gather 로 두 호출이 병행되는지 확인 (총 시간 < 합계)."""
        import asyncio
        import time

        async def slow_kw(*, query: str) -> list[KakaoPlace]:  # noqa: ARG001
            await asyncio.sleep(0.1)
            return [_place("약국A")]

        async def slow_loc(**_: Any) -> list[KakaoPlace]:
            await asyncio.sleep(0.1)
            return [_place("약국B", "2")]

        from ai_worker.domains.tool_calling import jobs as tt

        monkeypatch.setattr(tt, "search_hospitals_by_keyword", slow_kw)
        monkeypatch.setattr(tt, "search_hospitals_by_location", slow_loc)

        start = time.perf_counter()
        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_keyword",
                    "arguments": {"query": "역삼동"},
                },
                {
                    "tool_call_id": "c2",
                    "name": "search_hospitals_by_location",
                    "arguments": {"category": "약국"},
                    "geolocation": {"lat": 37.5, "lng": 127.0},
                },
            ],
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.18  # 순차였으면 0.2s 이상
        assert "c1" in result
        assert "c2" in result


class TestRunToolCallsJobErrorIsolation:
    @pytest.mark.asyncio
    async def test_one_call_fails_other_still_returns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """병렬 호출 중 한 쪽이 실패해도 성공한 호출 결과는 살아남는다."""

        async def ok_kw(*, query: str) -> list[KakaoPlace]:  # noqa: ARG001
            return [_place("정상약국")]

        async def fail_loc(**_: Any) -> list[KakaoPlace]:
            raise RuntimeError("kakao 5xx")

        from ai_worker.domains.tool_calling import jobs as tt

        monkeypatch.setattr(tt, "search_hospitals_by_keyword", ok_kw)
        monkeypatch.setattr(tt, "search_hospitals_by_location", fail_loc)

        result = await tt.run_tool_calls_job(
            calls=[
                {"tool_call_id": "c1", "name": "search_hospitals_by_keyword", "arguments": {"query": "x"}},
                {
                    "tool_call_id": "c2",
                    "name": "search_hospitals_by_location",
                    "arguments": {"category": "약국"},
                    "geolocation": {"lat": 37.5, "lng": 127.0},
                },
            ],
        )

        assert result["c1"]["places"][0]["place_name"] == "정상약국"
        assert "error" in result["c2"]
        assert "kakao 5xx" in result["c2"]["error"]


class TestRunToolCallsJobUnknownFunction:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        result = await tt.run_tool_calls_job(
            calls=[{"tool_call_id": "c1", "name": "do_magic", "arguments": {}}],
        )

        assert "error" in result["c1"]
        assert "unknown" in result["c1"]["error"].lower()


class TestRunToolCallsJobMissingGeolocation:
    @pytest.mark.asyncio
    async def test_location_call_without_geolocation_returns_error(self) -> None:
        from ai_worker.domains.tool_calling import jobs as tt

        result = await tt.run_tool_calls_job(
            calls=[
                {
                    "tool_call_id": "c1",
                    "name": "search_hospitals_by_location",
                    "arguments": {"category": "약국"},
                    # geolocation 키 없음
                },
            ],
        )

        assert "error" in result["c1"]
        assert "geolocation" in result["c1"]["error"].lower()
