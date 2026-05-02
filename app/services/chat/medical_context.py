"""사용자 의학 컨텍스트 빌더 — medication + Profile.health_survey → system prompt 섹션.

PLAN.md (feature/RAG) §2/§3 Step 0:
- medication 테이블에서 사용자 복용약 list 조회
- profiles.health_survey JSONField 에서 conditions/allergies/is_smoking 등 조회
- markdown 한국어 섹션으로 조립 → 2nd LLM 의 system prompt 의 [사용자 의학 컨텍스트]

음성응답 (is_smoking=False, is_drinking=False, conditions=[], allergies=[])
은 IntentClassifier 의 fan-out 시 query 안 만들도록 명시. 본 모듈은 raw fact 만.

흐름: profile_id → DB 조회 (medication + profiles) → markdown 섹션
"""

from uuid import UUID


async def build_medical_context(profile_id: UUID) -> str:
    """profile_id 로 사용자 의학 컨텍스트 markdown 섹션 작성.

    Args:
        profile_id: 대상 profile UUID. chat_session.profile_id 에서 추출.

    Returns:
        markdown 형식 한국어 컨텍스트. 예시:

            [사용자 의학 컨텍스트]
            - 복용 중인 약: 메트포민, 와파린, 오메가3, 타이레놀
            - 기저질환: 당뇨, 고혈압, 심장질환, 신장질환
            - 알레르기: 항생제, 소염제
            - 흡연: 비흡연
            - 음주: 비음주

        medication / health_survey 모두 비어있으면 빈 문자열 반환 (섹션 자체 생략).

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    raise NotImplementedError("medical_context 빌더는 Phase 3 [Implement] 에서 medication + Profile 조회로 채움")
