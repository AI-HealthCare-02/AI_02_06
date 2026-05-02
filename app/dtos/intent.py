"""IntentClassifier (4o-mini) 의 Structured Output Pydantic schema.

PLAN.md (feature/RAG) §3 Step 1+2 — Fastpath + Intent + fan-out 통합.
4o-mini 가 단일 호출로 다음을 결정:

- intent: greeting / out_of_scope / domain_question / ambiguous
- direct_answer: tool 호출 없이 즉시 답변할 텍스트 (greeting/out_of_scope/ambiguous)
- fanout_queries: domain_question 시 N+M+1 검색 query 리스트 (cap=10)
- referent_resolution: 대명사 → 명사 매핑 ({"그거": "타이레놀"} 등)
- filters: 메타데이터 필터 (target_drug, target_section)

OpenAI Structured Outputs (response_format=Pydantic) 로 100% JSON 스키마 강제.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class IntentType(StrEnum):
    """4o-mini 가 분류하는 4가지 의도 카테고리."""

    GREETING = "greeting"
    """단순 인사 — 'direct_answer' 에 친근한 응답."""

    OUT_OF_SCOPE = "out_of_scope"
    """도메인 외 (정치/시사/잡담/욕설/날씨 등) — 'direct_answer' 에 가이드 메시지."""

    DOMAIN_QUESTION = "domain_question"
    """의학/약학 도메인 질문 — 'fanout_queries' 로 RAG 검색 진입."""

    AMBIGUOUS = "ambiguous"
    """대명사가 있는데 history 에서 referent 를 못 찾음 — 'direct_answer' 에 명확화 질문."""


class SearchFilters(BaseModel):
    """RAG 검색 시 적용할 메타데이터 필터.

    Step 2 의 4o-mini 가 history + medical_context 를 분석해 결정.
    `MedicineChunk` 의 `medicine_name` (via JOIN) 과 `section` 컬럼에 적용.
    """

    target_drug: str | None = Field(
        None,
        description="단일 약품명 필터 (예: '타이레놀'). None 이면 전체.",
    )
    target_section: str | None = Field(
        None,
        description="MedicineChunkSection enum value (예: 'drug_interaction'). None 이면 전체.",
    )


class IntentClassification(BaseModel):
    """4o-mini IntentClassifier 의 Structured Output 결과.

    Pydantic max_length 로 fanout_queries cap=10 강제. OpenAI Structured Outputs
    이 schema 위반 자체를 차단해 ImagentClassifier 가 어길 위험 0.
    """

    model_config = ConfigDict(extra="forbid")

    intent: IntentType = Field(..., description="질의의 의도 카테고리")
    direct_answer: str | None = Field(
        None,
        description=(
            "intent 가 greeting/out_of_scope/ambiguous 일 때 즉시 응답할 텍스트. "
            "domain_question 일 때는 None (RAG 진입)."
        ),
    )
    fanout_queries: list[str] | None = Field(
        None,
        max_length=10,
        description=("intent 가 domain_question 일 때 RAG 검색용 query 리스트 (cap=10). 다른 intent 일 때는 None."),
    )
    referent_resolution: dict[str, str] | None = Field(
        None,
        description=(
            "대명사 → 명사 매핑. 예: {'그거': '타이레놀', '거기': '강남역'}. "
            "history 에 명시된 referent 만 인정 (hallucination 방지). "
            "없으면 None."
        ),
    )
    filters: SearchFilters | None = Field(
        None,
        description="RAG 검색 시 적용할 메타데이터 필터. domain_question 일 때만.",
    )
