"""Lifestyle guide prompt builder module.

Builds a structured GPT prompt for generating personalized lifestyle guides
based on a user's active medication list.
"""

import logging

logger = logging.getLogger(__name__)

_SYSTEM_TEMPLATE = """\
당신은 약학 및 건강 생활습관 전문가입니다.
아래에 나열된 활성 약물 정보를 바탕으로, 환자가 일상에서 실천할 수 있는
맞춤형 생활습관 가이드를 작성해 주세요.

## 활성 약물 목록
{medication_lines}

## 요청 사항
다음 5가지 카테고리 각각에 대해 구체적인 조언을 제공하세요:
- diet (식이요법)
- sleep (수면)
- exercise (운동)
- symptom (증상 모니터링)
- interaction (약물 상호작용 주의사항)

## 응답 형식
반드시 아래 JSON 스키마에 맞게 응답하세요. 다른 텍스트 없이 JSON만 반환하세요.

{{
  "diet": "<식이요법 조언>",
  "sleep": "<수면 조언>",
  "exercise": "<운동 조언>",
  "symptom": "<증상 모니터링 조언>",
  "interaction": "<약물 상호작용 주의사항>",
  "recommended_challenges": [
    {{
      "category": "<diet|sleep|exercise|symptom|interaction 중 하나>",
      "title": "<챌린지 제목>",
      "description": "<챌린지 설명>",
      "target_days": <목표 일수 정수>,
      "difficulty": "<쉬움|보통|어려움>"
    }}
  ]
}}

## 챌린지 생성 규칙
- 정확히 5개의 챌린지를 생성하세요.
- 5개의 카테고리(diet, sleep, exercise, symptom, interaction)에서 골고루 선정하세요.
- 난이도는 쉬움 2개, 보통 2개, 어려움 1개를 권장합니다.
- 목표 일수는 쉬움 7일, 보통 14일, 어려움 21일을 기준으로 하세요.
- 챌린지 제목은 구체적이고 실천 가능한 행동으로 작성하세요. (최대 30자)

"""


def _format_medication_line(med: dict) -> str:
    """Format a single medication dict into a human-readable line.

    Args:
        med: Medication dict with keys medicine_name, category,
             intake_instruction, dose_per_intake (all optional except name).

    Returns:
        Formatted string describing the medication.
    """
    name = med.get("medicine_name", "")
    parts = [f"- {name}"]

    category = med.get("category")
    if category:
        parts.append(f"[{category}]")

    instruction = med.get("intake_instruction")
    if instruction:
        parts.append(f"복용법: {instruction}")

    dose = med.get("dose_per_intake")
    if dose:
        parts.append(f"용량: {dose}")

    return " / ".join(parts) if len(parts) > 1 else parts[0]


def build_guide_prompt(meds: list[dict]) -> str:
    """Build a GPT prompt for generating a personalized lifestyle guide.

    Args:
        meds: List of active medication dicts. Each dict must contain
              'medicine_name' and optionally 'category', 'intake_instruction',
              'dose_per_intake'.

    Returns:
        A formatted prompt string requesting a JSON lifestyle guide.

    Raises:
        ValueError: If meds is empty (활성 약물 없음).
    """
    if not meds:
        raise ValueError("활성 약물 목록이 비어 있습니다. 가이드를 생성하려면 최소 1개의 활성 약물이 필요합니다.")

    medication_lines = "\n".join(_format_medication_line(med) for med in meds)
    return _SYSTEM_TEMPLATE.format(medication_lines=medication_lines)
