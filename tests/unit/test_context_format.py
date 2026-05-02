"""Unit tests for app.services.tools.context_format — RAG chunks → markdown 섹션.

Phase 2 [Test] (Red): stub 단계라 모든 케이스가 NotImplementedError.
Phase 3 [Implement] 에서 실 포맷 검증으로 전환.

PLAN.md §4.1 — F1 결정의 4가지 검증:
- chunks 리스트 → '[약: name] [section]: content' N줄
- 빈 chunks → 빈 문자열
- top-K cap (15) 초과 시 자르기
- 각 content 1500자 truncate
"""

from __future__ import annotations

import pytest

from app.services.tools.context_format import format_rag_context

SAMPLE_CHUNKS = [
    {
        "medicine_name": "타이레놀",
        "section": "drug_interaction",
        "content": "와파린과 병용 시 INR 상승으로 출혈 위험 증가.",
        "score": 0.95,
    },
    {
        "medicine_name": "와파린",
        "section": "drug_interaction",
        "content": "아세트아미노펜 병용 시 출혈 위험.",
        "score": 0.92,
    },
]


class TestFormatRagContext:
    """format_rag_context 단위 테스트 (Red 상태)."""

    def test_basic_format(self) -> None:
        """기본 케이스 — 2 chunks → 2줄 markdown."""
        with pytest.raises(NotImplementedError):
            format_rag_context(SAMPLE_CHUNKS)

    def test_empty_chunks(self) -> None:
        """빈 chunks → 빈 문자열."""
        with pytest.raises(NotImplementedError):
            format_rag_context([])

    def test_cap_applied(self) -> None:
        """20 chunks 입력 + cap=15 → 15 줄로 잘림."""
        chunks = [
            {"medicine_name": f"약{i}", "section": "overview", "content": "내용", "score": 0.5} for i in range(20)
        ]
        with pytest.raises(NotImplementedError):
            format_rag_context(chunks, cap=15)

    def test_long_content_truncated(self) -> None:
        """content 가 1500 자 초과 → truncate."""
        long = "가" * 5000
        chunks = [{"medicine_name": "약", "section": "overview", "content": long, "score": 0.9}]
        with pytest.raises(NotImplementedError):
            format_rag_context(chunks, max_content_chars=1500)
