"""Step 0 + Step 1+2 통합 오케스트레이터.

PLAN.md (feat/ingredient-grounded-rag) 변경:
- Step 0a: build_medical_context (medication + survey)
- Step 0b: 사용자 medication brand → 활성성분 SQL 매핑 (유사도 X)
- Step 0c: medical_context + [용어 매핑] 섹션을 IntentClassifier system 에 합성
- Step 1+2: classify_intent (4o-mini Structured Outputs)

흐름:
  profile_id -> build_medical_context (medication brand list + health_survey)
            -> map_brands_to_ingredients (medication brand -> ingredient names)
            -> classify_intent (medical_context + ingredient mapping 동시 입력)
            -> (medical_context, ingredient_mapping_section, classification) 반환

호출자 (message_service) 가 ingredient_mapping_section 을 2nd LLM 의
system_prompt 에도 그대로 prepend - brand <-> ingredient 단절 방지.
"""

import logging
from uuid import UUID

from app.dtos.intent import IntentClassification
from app.models.medication import Medication
from app.services.chat.ingredient_mapper import (
    format_ingredient_mapping_section,
    map_brands_to_ingredients,
)
from app.services.chat.medical_context import build_medical_context
from app.services.intent.classifier import classify_intent

logger = logging.getLogger(__name__)


async def classify_user_turn(
    profile_id: UUID,
    messages: list[dict[str, str]],
) -> tuple[str, str, IntentClassification]:
    """profile_id + history -> (medical_context, ingredient_mapping, classification).

    Args:
        profile_id: chat_session.profile_id 에서 추출.
        messages: 시간순 history + 마지막 user 메시지. system role 제외.

    Returns:
        ``(medical_context, ingredient_mapping_section, classification)``:
        - medical_context: ``[사용자 의학 컨텍스트]`` markdown (또는 빈 문자열)
        - ingredient_mapping_section: ``[용어 매핑]`` markdown (또는 빈 문자열)
        - classification: IntentClassification (direct_answer 또는 fanout)

        2nd LLM 의 system_prompt 에 prepend 할 수 있도록 둘 다 반환한다.
    """
    medical_context = await build_medical_context(profile_id)
    if medical_context:
        logger.info(
            "[Chat] medical_context loaded profile=%s len=%dchars",
            str(profile_id)[:8],
            len(medical_context),
        )

    # brand -> ingredient 매핑 (사용자 medication 만 - 질의 약 이름은 LLM 이 추출)
    user_medication_names = await _load_medication_names(profile_id)
    mapping = await map_brands_to_ingredients(user_medication_names)
    ingredient_mapping_section = format_ingredient_mapping_section(mapping)
    if ingredient_mapping_section:
        logger.info(
            "[Chat] ingredient_mapping built profile=%s brands=%d mapped=%d",
            str(profile_id)[:8],
            len(mapping),
            sum(1 for v in mapping.values() if v),
        )

    # IntentClassifier 의 system 에는 medical_context + ingredient_mapping_section
    # 를 함께 합쳐 fanout 을 성분명 위주로 유도.
    classifier_extra = "\n\n".join(s for s in (medical_context, ingredient_mapping_section) if s)
    classification = await classify_intent(messages, medical_context=classifier_extra or None)
    logger.info(
        "[Chat] intent=%s queries=%d direct_answer=%s",
        classification.intent.value,
        len(classification.fanout_queries) if classification.fanout_queries else 0,
        "yes" if classification.direct_answer else "no",
    )
    return medical_context, ingredient_mapping_section, classification


async def _load_medication_names(profile_id: UUID) -> list[str]:
    """사용자의 활성 medication 의 brand 이름 list."""
    rows = (
        await Medication
        .filter(profile_id=profile_id, is_active=True, deleted_at__isnull=True)
        .order_by("created_at")
        .values_list("medicine_name", flat=True)
    )
    return list(rows)
