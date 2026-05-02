"""IntentClassifier — 4o-mini 기반 Step 1+2 통합 (Fastpath + Intent + fan-out).

PLAN.md (feature/RAG) §3:
- Fastpath (인사/욕설/도메인외) → direct_answer 즉시 응답
- 도메인 질문 → fanout_queries 생성 (cap=10, 임상 우선순위 자율 cut)
- 대명사 풀이 → referent_resolution
- 메타데이터 필터 → filters (target_drug, target_section)

OpenAI Structured Outputs 로 IntentClassification Pydantic schema 100% 강제.

흐름: messages + medical_context → 4o-mini → IntentClassification
"""

from app.dtos.intent import IntentClassification


async def classify_intent(
    messages: list[dict[str, str]],
    medical_context: str | None = None,
) -> IntentClassification:
    """사용자 query + history + medical_context → IntentClassification.

    Args:
        messages: 시간순 history (system role 제외, user/assistant 만).
        medical_context: 사용자 의학 컨텍스트 markdown (medication +
            health_survey 통합). None 이면 빈 컨텍스트.

    Returns:
        IntentClassification — intent + direct_answer 또는 fanout_queries +
        referent_resolution + filters.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현. Phase 3 Implement 에서 채움.
    """
    raise NotImplementedError("IntentClassifier 는 Phase 3 [Implement] 에서 4o-mini Structured Outputs 로 채움")
