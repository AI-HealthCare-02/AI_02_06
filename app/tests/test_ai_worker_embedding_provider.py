"""AI-Worker 임베딩 프로바이더 계약 테스트.

`ai_worker/providers/embedding.py`의 핵심 함수들을 검증한다:

- preprocess: Korean pharmaceutical term normalization (순수 함수)
- normalize:  L2-정규화 (순수 함수)
- encode_text: ko-sroberta 모델을 통한 768차원 임베딩 (integration)
- 모델 싱글톤: 여러 호출에서 같은 인스턴스 재사용

Phase X-2 의 목표는 FastAPI에 있던 임베딩 로직을 AI-Worker로 이전하는 것이다.
테스트는 다음 두 레벨로 구성:
1. 순수 함수 (빠름): preprocess, normalize
2. integration (느림, 모델 로드 동반): encode_text + rag_tasks.embed_text_job
"""

import math

import pytest

from ai_worker.providers import embedding as emb
from ai_worker.tasks import rag_tasks

# ── 순수 함수 (빠름) ────────────────────────────────────────────────


class TestPreprocess:
    """전처리 — 한국어 의약품 용어 정규화."""

    def test_strips_whitespace(self) -> None:
        assert emb._preprocess("  활명수  ") == "활명수"

    def test_collapses_internal_spaces(self) -> None:
        assert emb._preprocess("활명수    효능") == "활명수 효능"

    def test_normalizes_efficacy_punctuation(self) -> None:
        assert "효능 효과" in emb._preprocess("효능·효과가 좋다")

    def test_normalizes_usage_punctuation(self) -> None:
        assert "용법 용량" in emb._preprocess("용법·용량 기준")

    def test_empty_string_returns_empty(self) -> None:
        assert emb._preprocess("") == ""


class TestNormalize:
    """L2-정규화."""

    def test_unit_vector_becomes_unit(self) -> None:
        result = emb._normalize([1.0, 0.0, 0.0])
        assert math.isclose(result[0], 1.0)
        assert result[1] == 0.0

    def test_l2_norm_is_one(self) -> None:
        result = emb._normalize([3.0, 4.0])
        norm = math.sqrt(result[0] ** 2 + result[1] ** 2)
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

    def test_zero_vector_passes_through(self) -> None:
        assert emb._normalize([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


class TestConstants:
    """모듈 레벨 상수 계약."""

    def test_embedding_dimensions(self) -> None:
        assert emb.EMBEDDING_DIMENSIONS == 768

    def test_embedding_model_name(self) -> None:
        assert emb.EMBEDDING_MODEL_NAME == "jhgan/ko-sroberta-multitask"


# ── Integration (모델 로드 동반, 느림) ──────────────────────────────


@pytest.mark.asyncio
class TestEncodeTextIntegration:
    """실제 ko-sroberta 모델을 한 번 로드해서 계약 검증한다.

    첫 테스트는 모델 로딩 시간(~30초) 포함. 이후 테스트는 싱글톤 재사용.
    """

    async def test_returns_768_dim_vector(self) -> None:
        result = await emb.encode_text("활명수 효능")
        assert len(result) == 768

    async def test_l2_normalized(self) -> None:
        result = await emb.encode_text("활명수 효능")
        norm = math.sqrt(sum(x * x for x in result))
        assert math.isclose(norm, 1.0, abs_tol=1e-4)

    async def test_empty_string_returns_zero_vector(self) -> None:
        result = await emb.encode_text("")
        assert len(result) == 768
        assert all(x == 0.0 for x in result)

    async def test_deterministic_output(self) -> None:
        v1 = await emb.encode_text("활명수")
        v2 = await emb.encode_text("활명수")
        # Same input → same vector (within float tolerance)
        for a, b in zip(v1, v2, strict=True):
            assert math.isclose(a, b, abs_tol=1e-5)


@pytest.mark.asyncio
class TestEmbedTextJobIntegration:
    """rag_tasks.embed_text_job 이 encode_text 로 위임하는지 확인."""

    async def test_job_returns_768_dim(self) -> None:
        result = await rag_tasks.embed_text_job("페니라민정 효능")
        assert len(result) == 768

    async def test_job_result_is_l2_normalized(self) -> None:
        result = await rag_tasks.embed_text_job("디고신정")
        norm = math.sqrt(sum(x * x for x in result))
        assert math.isclose(norm, 1.0, abs_tol=1e-4)

    async def test_job_no_longer_raises_not_implemented(self) -> None:
        # Phase X-2 전: NotImplementedError. 본 테스트는 그 제거를 강제한다.
        try:
            await rag_tasks.embed_text_job("x")
        except NotImplementedError:
            pytest.fail("embed_text_job should be implemented in Phase X-2")
