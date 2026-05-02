"""RAG context formatter — chunks list → 2nd LLM system prompt 의 검색 결과 섹션.

PLAN.md (feature/RAG) §3 F1 — `[약: name][section]: content` 포맷 명시.

정책:
- top-N cap (기본 15) 으로 token 폭발 차단
- 각 chunk content 1500 자 truncate (안전 마진)
- 섹션 한국어 표시 (DRUG_INTERACTION → '약물 상호작용' 등)
- 빈 chunks 면 빈 문자열 반환 (섹션 자체 생략 가능)
"""

from typing import Any


def format_rag_context(chunks: list[dict[str, Any]], cap: int = 15, max_content_chars: int = 1500) -> str:
    """RAG retrieval 결과 chunks 를 2nd LLM 친화 markdown 섹션으로 조립.

    Args:
        chunks: ai_worker.rag.retrieval._serialize_chunks 의 결과. 각 dict 는
            {medicine_name, section, content, score} 키 보유.
        cap: 최종 포함할 chunk 수 상한. 기본 15 (lost-in-middle 회피).
        max_content_chars: 각 chunk content 의 최대 char 수. 기본 1500.

    Returns:
        markdown 섹션. 예시:

            [약: 타이레놀] [drug_interaction]: 와파린과 병용 시 INR 상승...
            [약: 와파린] [drug_interaction]: 아세트아미노펜 병용 시 출혈 위험...
            ...

        빈 chunks 면 빈 문자열.

    Raises:
        NotImplementedError: 본 stub 단계에서는 미구현.
    """
    del chunks, cap, max_content_chars
    msg = "format_rag_context 는 Phase 3 [Implement] 에서 채움"
    raise NotImplementedError(msg)
