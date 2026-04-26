"""RAG 파이프라인 orchestrator (얇은 entry).

본 모듈은 RAG 도메인 안에서 **유일한 클래스/객체 형태**다. 사용자 룰에
따라 RAG 의 모든 실제 작업은 함수형 모듈로 분해돼 있고, 본 파이프라인은
그 함수들을 호출하는 얇은 코디네이터일 뿐이다.

쓰임새:
- ``ai_worker.domains.rag.jobs`` 의 RQ task 가 본 파이프라인 인스턴스 또는
  바로 함수형 모듈을 호출
- 외부(테스트·다른 도메인)는 ``embed`` / ``rewrite`` / ``generate`` 메서드의
  통일된 진입점을 통해 RAG 능력을 호출 가능

상태를 보유하지 않으므로 매 호출마다 새 인스턴스를 만들어도 비용 0.
"""

from ai_worker.domains.rag.embedding_provider import encode_text
from ai_worker.domains.rag.query_rewriter import rewrite_user_query
from ai_worker.domains.rag.response_generator import generate_response
from app.dtos.rag import ChatCompletion, RewriteResult


class RAGPipeline:
    """RAG 도메인 함수들의 단일 진입점 (orchestrator)."""

    async def embed(self, text: str) -> list[float]:
        """문자열을 768차원 임베딩 벡터로 변환한다."""
        return await encode_text(text)

    async def rewrite(self, history: list[dict[str, str]], current_query: str) -> RewriteResult:
        """다중 턴 쿼리를 self-contained 한 문장으로 재작성한다."""
        return await rewrite_user_query(history=history, current_query=current_query)

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> ChatCompletion:
        """대화 + system prompt 로 답변을 생성한다."""
        return await generate_response(messages=messages, system_prompt=system_prompt)
