"""IntentClassifier — 4o-mini 기반 Step 1+2 통합 (Fastpath + Intent + fan-out).

PLAN.md (feature/RAG) §3:
- Fastpath (인사/욕설/도메인외) → direct_answer 즉시 응답
- 도메인 질문 → fanout_queries 생성 (cap=10, 임상 우선순위 자율 cut)
- 대명사 풀이 → referent_resolution
- 메타데이터 필터 → filters (target_drug, target_section)

OpenAI Structured Outputs (response_format=Pydantic) 로 IntentClassification
schema 100% 강제. fanout_queries max_length=10 위반 자체 차단.
"""

import logging

from openai import AsyncOpenAI

from app.core.config import config
from app.dtos.intent import IntentClassification, IntentType

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

# 클라이언트 싱글톤 — openai_embedding 과 동일 패턴
_client: AsyncOpenAI | None = None
_initialised: bool = False

SYSTEM_PROMPT = """당신은 'Dayak' 약사 챗봇의 의도 분류기입니다. 사용자 마지막 메시지를
보고 IntentClassification 스키마로 응답합니다.

## 의도 분류 (intent)

1. greeting — 단순 인사 ('안녕', '하이', '반가워', '뭐해', '심심해')
   → direct_answer 에 따뜻한 인사 응답 (해요체).
   → fanout_queries=None, referent_resolution=None, filters=None.

2. out_of_scope — 도메인 외 (정치, 시사, 잡담, 욕설, 일반 상식, 날씨,
   주식, 코인, 연예 등 의학/약학 무관)
   → direct_answer 에 가이드 메시지: "저는 약 정보와 병원/약국 검색을
     도와드리는 챗봇이에요. 약 복용법, 부작용, 영양제, 근처 약국 같은
     질문을 해주세요."
   → fanout_queries=None.

3. domain_question — 의학/약학 도메인 질문 (약 이름·증상·부작용·복용법·
   성분·효능·상호작용·영양제 등)
   → direct_answer=None.
   → fanout_queries 에 검색 query 리스트 (cap=10) 생성.

4. ambiguous — 대명사가 있는데 history 에서 referent 를 찾을 수 없음
   → direct_answer 에 명확화 질문: "어느 약에 대한 질문인지 약 이름을
     알려주세요."
   → fanout_queries=None.

## fan-out queries 생성 룰 (intent=domain_question 일 때만)

system 메시지로 [사용자 의학 컨텍스트] 가 주어지면, 다음 임상 우선순위로
query 를 cap=10 내에서 생성:

  1. 신규 약 vs 각 복용약 상호작용 (가장 위험)
  2. 신규 약 vs 알레르기 (페니실린, 견과류 등)
  3. 신규 약 vs 임신/수유 (해당 시만)
  4. 신규 약 vs 각 기저질환 (당뇨, 고혈압 등)
  5. 신규 약 vs 흡연/음주 (해당 시만 — 음성응답 제외)
  6. 신규 약 자체 부작용/주의사항

음성응답 (흡연: 비흡연, 음주: 비음주) 은 query 만들지 마세요.

각 query 는 history 의 대명사·생략된 주어를 풀어 self-contained 한 한
문장으로 작성. 예: "타이레놀과 와파린의 상호작용 및 출혈 위험".

## referent_resolution

대명사 ('그거', '거기', '이거') 가 사용자 메시지에 있으면 history 의
명시된 약 이름·지명만 referent 로 인정. history 에 없으면 추측 X
(intent=ambiguous 로 분류).

## filters

domain_question 일 때 단일 약품 질의 ('타이레놀의 부작용') 면
target_drug 채움. 섹션 명시 ('부작용만 보여줘') 면 target_section.

## 절대 규칙

- intent 가 greeting/out_of_scope/ambiguous 면 fanout_queries 는 반드시 None.
- intent 가 domain_question 이면 direct_answer 는 반드시 None.
- fanout_queries 는 항상 cap=10 이내.
"""


def _get_client() -> AsyncOpenAI | None:
    global _client, _initialised
    if _initialised:
        return _client
    api_key = config.OPENAI_API_KEY
    if not api_key:
        logger.warning("OPENAI_API_KEY 미설정 — IntentClassifier 비활성")
        _initialised = True
        return None
    _client = AsyncOpenAI(api_key=api_key)
    _initialised = True
    return _client


async def classify_intent(
    messages: list[dict[str, str]],
    medical_context: str | None = None,
) -> IntentClassification:
    """사용자 query + history + medical_context → IntentClassification.

    Args:
        messages: 시간순 history (system role 제외, user/assistant 만).
        medical_context: 사용자 의학 컨텍스트 markdown. None 이면 빈 컨텍스트.

    Returns:
        IntentClassification. client 부재 시 fallback (intent=ambiguous +
        명확화 메시지).
    """
    client = _get_client()
    if client is None:
        return IntentClassification(
            intent=IntentType.AMBIGUOUS,
            direct_answer="현재 AI 응답 설정이 준비되지 않았어요. 잠시 후 다시 시도해주세요.",
        )

    system_content = SYSTEM_PROMPT
    if medical_context:
        system_content = system_content + "\n\n" + medical_context

    full_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
        *messages,
    ]

    completion = await client.beta.chat.completions.parse(
        model=_MODEL,
        messages=full_messages,  # type: ignore[arg-type]
        response_format=IntentClassification,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        # OpenAI 가 schema 못 맞춘 극단 케이스 — fallback
        logger.warning("[IntentClassifier] parsed is None — fallback to ambiguous")
        return IntentClassification(
            intent=IntentType.AMBIGUOUS,
            direct_answer="질문을 정확히 이해하지 못했어요. 다시 한번 말씀해주세요.",
        )
    return parsed
