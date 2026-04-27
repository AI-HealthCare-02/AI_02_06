"""AI-Worker Router LLM provider 계약 테스트 (Y-5 Red).

``ai_worker/domains/tool_calling/router_llm.py`` 의 ``route_with_tools`` 는 OpenAI
``chat.completions.create`` 를 ``tools=TOOL_SCHEMAS``,
``parallel_tool_calls=True`` 로 호출하고, 응답 ``choices[0].message`` 를
dict 로 정규화해 반환한다. 그 dict 는 ``parse_router_response`` 가 그대로
받아 ``RouteResult`` 로 변환할 수 있는 형태여야 한다.

본 테스트는 OpenAI client 호출만 mock 으로 검증한다.
"""

import inspect
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRouteWithToolsSignature:
    def test_is_async(self) -> None:
        from ai_worker.domains.tool_calling import router_llm as router_provider

        assert inspect.iscoroutinefunction(router_provider.route_with_tools)

    def test_signature_has_messages(self) -> None:
        from ai_worker.domains.tool_calling import router_llm as router_provider

        sig = inspect.signature(router_provider.route_with_tools)
        assert "messages" in sig.parameters


class TestRouteWithToolsCallContract:
    @pytest.mark.asyncio
    async def test_uses_parallel_tool_calls_true_and_tool_schemas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import router_llm as router_provider
        from app.services.tools.schemas import TOOL_SCHEMAS

        captured: dict[str, Any] = {}

        # OpenAI 응답 형태를 흉내내는 mock
        msg = MagicMock()
        msg.content = None
        msg.tool_calls = [
            MagicMock(
                id="call_1",
                type="function",
                function=MagicMock(name_attr=None),
            ),
        ]
        msg.tool_calls[0].function.name = "search_hospitals_by_keyword"
        msg.tool_calls[0].function.arguments = json.dumps({"query": "강남역 약국"})
        choice = MagicMock(message=msg)
        completion = MagicMock(choices=[choice])

        async def fake_create(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return completion

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(router_provider, "get_openai_client", lambda: fake_client)

        msgs = [{"role": "user", "content": "강남역 약국 알려줘"}]
        result = await router_provider.route_with_tools(messages=msgs)

        # 옵션 C: route_with_tools 가 ROUTER_SYSTEM_PROMPT 를 system role 로
        # 자동 prepend 한다. 호출 측 messages 는 그 뒤에 그대로 따라붙어야 함.
        sent = captured["messages"]
        assert sent[0]["role"] == "system"
        assert sent[0]["content"] == router_provider.ROUTER_SYSTEM_PROMPT
        assert sent[1:] == msgs
        assert captured["tools"] == TOOL_SCHEMAS
        assert captured["tool_choice"] == "auto"
        assert captured["parallel_tool_calls"] is True

        # 결과 dict 가 parse_router_response 입력 형태와 일치해야 함
        assert result["role"] == "assistant"
        assert result["content"] is None
        assert isinstance(result["tool_calls"], list)
        assert result["tool_calls"][0]["id"] == "call_1"
        assert result["tool_calls"][0]["function"]["name"] == "search_hospitals_by_keyword"

    @pytest.mark.asyncio
    async def test_text_response_yields_dict_with_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_worker.domains.tool_calling import router_llm as router_provider

        msg = MagicMock()
        msg.content = "안녕하세요"
        msg.tool_calls = None
        choice = MagicMock(message=msg)
        completion = MagicMock(choices=[choice])

        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=completion)

        monkeypatch.setattr(router_provider, "get_openai_client", lambda: fake_client)

        result = await router_provider.route_with_tools(messages=[{"role": "user", "content": "안녕"}])

        assert result["content"] == "안녕하세요"
        assert result["tool_calls"] is None or result["tool_calls"] == []
