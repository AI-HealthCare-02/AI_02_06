"""Unit tests for app.services.chat.fanout_tool_calls."""

from __future__ import annotations

from app.dtos.intent import IntentClassification, IntentType
from app.services.chat.fanout_tool_calls import fanout_to_tool_calls


class TestFanoutToToolCalls:
    """fanout_to_tool_calls 단위 테스트."""

    def test_three_queries_to_three_tool_calls(self) -> None:
        c = IntentClassification(
            intent=IntentType.DOMAIN_QUESTION,
            fanout_queries=[
                "타이레놀과 메트포민의 상호작용",
                "타이레놀과 와파린의 상호작용",
                "타이레놀의 일반 부작용",
            ],
        )
        tool_calls = fanout_to_tool_calls(c)
        assert len(tool_calls) == 3
        for tc, q in zip(tool_calls, c.fanout_queries or [], strict=True):
            assert tc.name == "search_medicine_knowledge_base"
            assert tc.arguments == {"query": q}
            assert tc.needs_geolocation is False
            assert tc.tool_call_id.startswith("call_")

    def test_empty_fanout_returns_empty(self) -> None:
        c = IntentClassification(intent=IntentType.GREETING, direct_answer="안녕")
        assert fanout_to_tool_calls(c) == []

    def test_none_fanout_returns_empty(self) -> None:
        c = IntentClassification(
            intent=IntentType.DOMAIN_QUESTION,
            fanout_queries=None,
        )
        assert fanout_to_tool_calls(c) == []

    def test_unique_tool_call_ids(self) -> None:
        """동일 query 가 반복돼도 tool_call_id 는 모두 unique."""
        c = IntentClassification(
            intent=IntentType.DOMAIN_QUESTION,
            fanout_queries=["같은 query", "같은 query", "같은 query"],
        )
        ids = [tc.tool_call_id for tc in fanout_to_tool_calls(c)]
        assert len(ids) == len(set(ids))
