"""AI-Worker RAG task 계약 테스트 (옵션 C 이후 잔여).

FastAPI 프로세스에서 ML(임베딩/LLM)을 떼어내 AI-Worker로 옮기기 위한
RQ 작업 2종의 **시그니처·입출력 계약**을 락한다. 옵션 C 에서
``rewrite_query_job`` 은 폐기됐다.

Contract lock:
- embed_text_job(text)                      -> list[float]   (768 dim)
- generate_chat_response_job(context, query, history) -> dict (reply, tokens)

모든 함수는 async (RQ 2.x native async job) 로 구현되어야 한다.
"""

import inspect

from ai_worker.domains.rag import jobs as rag_tasks


class TestEmbedTextJobSignature:
    """embed_text_job — 쿼리 임베딩 RQ job."""

    def test_exists(self) -> None:
        assert hasattr(rag_tasks, "embed_text_job")

    def test_is_async(self) -> None:
        assert inspect.iscoroutinefunction(rag_tasks.embed_text_job), "RQ 2.x native async job 규약: async def 여야 함"

    def test_signature_has_text_param(self) -> None:
        sig = inspect.signature(rag_tasks.embed_text_job)
        assert "text" in sig.parameters

    def test_text_param_is_str(self) -> None:
        sig = inspect.signature(rag_tasks.embed_text_job)
        assert sig.parameters["text"].annotation is str


class TestRewriteQueryJobRemoved:
    """옵션 C: rewrite_query_job 은 폐기됐다 (Router LLM 가 흡수)."""

    def test_does_not_exist(self) -> None:
        assert not hasattr(rag_tasks, "rewrite_query_job")


class TestGenerateChatResponseJobSignature:
    """generate_chat_response_job — 최종 답변 생성 RQ job.

    파이프라인 호출 패턴:
    ``generate_chat_response(messages, system_prompt=...)`` 를 그대로 따라간다.
    context 삽입은 FastAPI 측 ``RAGPipeline._build_context`` 가 수행하므로
    이 job 은 LLM API 호출 자체만 책임진다.
    """

    def test_exists(self) -> None:
        assert hasattr(rag_tasks, "generate_chat_response_job")

    def test_is_async(self) -> None:
        assert inspect.iscoroutinefunction(rag_tasks.generate_chat_response_job)

    def test_signature_has_messages_and_system_prompt(self) -> None:
        sig = inspect.signature(rag_tasks.generate_chat_response_job)
        params = set(sig.parameters.keys())
        assert "messages" in params
        assert "system_prompt" in params


class TestModuleExports:
    """공개 API로 두 함수가 노출되어야 FastAPI 쪽에서 enqueue 가능."""

    def test_remaining_two_exported(self) -> None:
        public = {name for name in dir(rag_tasks) if not name.startswith("_")}
        assert "embed_text_job" in public
        assert "generate_chat_response_job" in public
        # 옵션 C: rewrite_query_job 은 export 되지 말아야 함
        assert "rewrite_query_job" not in public
