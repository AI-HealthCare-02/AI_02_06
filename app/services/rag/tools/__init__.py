"""Tool router for intent-based tool execution.

Routes tool-based intents to their respective implementations.
Each tool handles a specific intent category.

Phase 1: Stub implementations returning placeholder responses.
Phase 2: Real implementations (DB queries, external APIs).
"""

import logging

from app.services.rag.intent.intents import IntentType

logger = logging.getLogger(__name__)

_TOOL_STUBS: dict[IntentType, str] = {
    IntentType.MY_SCHEDULE: "복약 일정 조회 기능은 준비 중입니다.",
    IntentType.NEARBY_HOSPITAL: "주변 병원/약국 검색 기능은 준비 중입니다.",
    IntentType.WEATHER: "날씨 정보 기능은 준비 중입니다.",
}


class ToolRouter:
    """Routes tool-based intents to their implementations.

    Extend by registering new tool handlers for each IntentType.
    """

    async def execute(self, intent: IntentType, query: str, context: dict) -> str:  # noqa: ARG002
        """Execute the appropriate tool for the given intent.

        Args:
            intent: Classified user intent.
            query: Original user query.
            context: Additional context (history, user_profile_id, etc.).

        Returns:
            Tool response string.
        """
        handler = _TOOL_STUBS.get(intent)
        if handler:
            logger.info("Tool stub executed for intent: %s", intent)
            return handler

        logger.warning("No tool registered for intent: %s", intent)
        return "해당 기능은 아직 준비 중입니다."
