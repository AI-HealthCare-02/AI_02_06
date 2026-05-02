"""Step 0 + Step 1+2 통합 오케스트레이터.

PLAN.md (feature/RAG) §3 의 첫 두 단계를 단일 진입점으로 묶는다.
MessageService.ask_with_tools 가 본 함수만 호출하면 medical_context 빌드 +
4o-mini IntentClassifier 호출이 한 흐름으로 처리된다.

흐름:
  profile_id → build_medical_context (medication + survey)
            → classify_intent (4o-mini Structured Outputs)
            → IntentClassification 반환
"""

import logging
from uuid import UUID

from app.dtos.intent import IntentClassification
from app.services.chat.medical_context import build_medical_context
from app.services.intent.classifier import classify_intent

logger = logging.getLogger(__name__)


async def classify_user_turn(
    profile_id: UUID,
    messages: list[dict[str, str]],
) -> IntentClassification:
    """profile_id + history → IntentClassification (medical_context 자동 주입).

    Args:
        profile_id: chat_session.profile_id 에서 추출.
        messages: 시간순 history + 마지막 user 메시지. system role 제외.

    Returns:
        IntentClassification — direct_answer 또는 fanout_queries 가 채워진 결과.
    """
    medical_context = await build_medical_context(profile_id)
    if medical_context:
        logger.info(
            "[Chat] medical_context loaded profile=%s len=%dchars",
            str(profile_id)[:8],
            len(medical_context),
        )
    classification = await classify_intent(messages, medical_context=medical_context or None)
    logger.info(
        "[Chat] intent=%s queries=%d direct_answer=%s",
        classification.intent.value,
        len(classification.fanout_queries) if classification.fanout_queries else 0,
        "yes" if classification.direct_answer else "no",
    )
    return classification
