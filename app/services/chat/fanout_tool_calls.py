"""IntentClassification.fanout_queries → ToolCall list 변환.

PLAN.md (feature/RAG) §3 Step 3 — IntentClassifier 가 결정한 fanout_queries
N개를 search_medicine_knowledge_base tool_call N개로 변환. 기존 Router LLM
이 만들던 ToolCall 형식과 동일하게 만들어 ai_worker.run_tool_calls_job 이
변경 없이 재사용 가능.

흐름:
  IntentClassification (fanout_queries=[q1, q2, ...]) → [
    ToolCall(tool_call_id=..., name="search_medicine_knowledge_base",
             arguments={"query": q1}),
    ToolCall(..., arguments={"query": q2}),
    ...
  ]
"""

import uuid

from app.dtos.intent import IntentClassification
from app.dtos.tools import ToolCall

_RAG_TOOL_NAME = "search_medicine_knowledge_base"


def fanout_to_tool_calls(classification: IntentClassification) -> list[ToolCall]:
    """fanout_queries 를 search_medicine_knowledge_base tool_call list 로 변환.

    Args:
        classification: 4o-mini IntentClassifier 의 결과.

    Returns:
        ToolCall list. fanout_queries 가 None / 빈 list 면 빈 list 반환.
        각 ToolCall 의 tool_call_id 는 새 UUID, needs_geolocation=False
        (RAG retrieval 은 GPS 무관).
    """
    queries = classification.fanout_queries
    if not queries:
        return []

    return [
        ToolCall(
            tool_call_id=f"call_{uuid.uuid4().hex[:16]}",
            name=_RAG_TOOL_NAME,
            arguments={"query": query},
            needs_geolocation=False,
        )
        for query in queries
    ]
