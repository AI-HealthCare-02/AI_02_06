"""Unit tests for the summarization prompt builder.

Verifies the Role/Rule/Task/Output structure and user-prompt rendering of
``RAGGenerator._build_summary_prompt`` (Phase Z-A, PLAN.md Z-7).
"""

from ai_worker.utils.rag import RAGGenerator, _strip_code_fence


class TestSummarySystemPrompt:
    def test_system_prompt_has_role_rule_task_output_sections(self) -> None:
        prompt = RAGGenerator._build_summary_system_prompt()

        for header in ("# Role", "# Rule", "# Task", "# Output Format"):
            assert header in prompt, f"missing section: {header}"

    def test_system_prompt_forbids_out_of_scope_retention(self) -> None:
        prompt = RAGGenerator._build_summary_system_prompt()
        # Rule must explicitly instruct to drop non-medical noise.
        assert "의료" in prompt
        assert "제외" in prompt or "무관" in prompt

    def test_system_prompt_preserves_medication_facts(self) -> None:
        prompt = RAGGenerator._build_summary_system_prompt()
        # Drug names / symptoms / allergies must be preserved verbatim.
        assert "약품명" in prompt
        assert "알레르기" in prompt

    def test_system_prompt_caps_length(self) -> None:
        prompt = RAGGenerator._build_summary_system_prompt()
        assert "300자" in prompt

    def test_system_prompt_requires_markdown_output(self) -> None:
        """The summary must be persisted as Markdown, so the prompt must ask for it."""
        prompt = RAGGenerator._build_summary_system_prompt()
        assert "Markdown" in prompt or "마크다운" in prompt

    def test_system_prompt_forbids_code_fence_wrapping(self) -> None:
        """The LLM must emit markdown body directly, not wrapped in a ``` fence."""
        prompt = RAGGenerator._build_summary_system_prompt()
        assert "코드블록" in prompt

    def test_system_prompt_declares_section_headers(self) -> None:
        """Downstream rendering depends on the '## <section>' skeleton being present."""
        prompt = RAGGenerator._build_summary_system_prompt()
        for header in ("## 한 줄 요약", "## 복용 중인 약", "## 증상", "## 알레르기"):
            assert header in prompt, f"missing header spec: {header}"


class TestSummaryUserPrompt:
    def test_user_prompt_includes_prev_summary_when_present(self) -> None:
        messages = [
            {"role": "user", "content": "타이레놀 복용 중"},
            {"role": "assistant", "content": "타이레놀은 하루 최대 4g..."},
        ]

        rendered = RAGGenerator._build_summary_user_prompt(
            prev_summary="사용자는 편두통으로 타이레놀 복용 중.",
            messages=messages,
        )

        assert "[이전 요약]" in rendered
        assert "편두통으로 타이레놀 복용 중" in rendered
        assert "[새 대화 로그]" in rendered

    def test_user_prompt_marks_prev_summary_absent(self) -> None:
        rendered = RAGGenerator._build_summary_user_prompt(
            prev_summary=None,
            messages=[
                {"role": "user", "content": "타이레놀 복용 중"},
                {"role": "assistant", "content": "타이레놀 안내..."},
            ],
        )

        assert "[이전 요약]" in rendered
        assert "(없음)" in rendered

    def test_user_prompt_treats_blank_prev_summary_as_absent(self) -> None:
        rendered = RAGGenerator._build_summary_user_prompt(
            prev_summary="   ",
            messages=[
                {"role": "user", "content": "타이레놀 복용 중"},
                {"role": "assistant", "content": "타이레놀 안내..."},
            ],
        )

        assert "(없음)" in rendered

    def test_user_prompt_renders_messages_in_order(self) -> None:
        messages = [
            {"role": "user", "content": "첫 질문"},
            {"role": "assistant", "content": "첫 답변"},
            {"role": "user", "content": "두번째 질문"},
            {"role": "assistant", "content": "두번째 답변"},
        ]

        rendered = RAGGenerator._build_summary_user_prompt(
            prev_summary=None,
            messages=messages,
        )

        idx = [rendered.find(text) for text in ("첫 질문", "첫 답변", "두번째 질문", "두번째 답변")]
        assert all(i >= 0 for i in idx)
        assert idx == sorted(idx), "messages must be rendered in chronological order"

    def test_user_prompt_labels_roles_distinctly(self) -> None:
        rendered = RAGGenerator._build_summary_user_prompt(
            prev_summary=None,
            messages=[
                {"role": "user", "content": "질문입니다"},
                {"role": "assistant", "content": "답변입니다"},
            ],
        )

        assert "USER" in rendered or "사용자" in rendered
        assert "ASSISTANT" in rendered or "AI" in rendered or "약사" in rendered


class TestStripCodeFence:
    """Defensive fence-stripping for markdown summary persistence."""

    def test_leaves_plain_markdown_intact(self) -> None:
        body = "## 한 줄 요약\n사용자는 타이레놀 복용 중."
        assert _strip_code_fence(body) == body

    def test_strips_generic_triple_backtick_fence(self) -> None:
        raw = "```\n## 한 줄 요약\n사용자는 타이레놀 복용 중.\n```"
        assert _strip_code_fence(raw) == "## 한 줄 요약\n사용자는 타이레놀 복용 중."

    def test_strips_markdown_labelled_fence(self) -> None:
        raw = "```markdown\n## 한 줄 요약\n본문.\n```"
        assert _strip_code_fence(raw) == "## 한 줄 요약\n본문."

    def test_handles_trailing_whitespace_around_fence(self) -> None:
        raw = "   ```\n본문만\n```   \n"
        assert _strip_code_fence(raw) == "본문만"
