"""AI-Worker local embedding provider.

Hosts the ko-sroberta SentenceTransformer model as a process-wide
singleton inside the AI-Worker. FastAPI enqueues `embed_text_job`
via RQ; that job delegates to :func:`encode_text` here so the heavy
model weights never touch the FastAPI process.

Design notes:
- Model loading is ~30 seconds and ~420 MB RSS, so we create exactly
  one instance per worker process and warm it up at first use.
- ``SentenceTransformer.encode`` is CPU-bound and releases the GIL in
  PyTorch C++ internals, so a small ThreadPoolExecutor lets multiple
  RQ jobs encode concurrently without spawning extra processes.
- Public surface (``encode_text``) is async so it integrates cleanly
  with RQ 2.x native async jobs.

Phase X-2 ships :func:`encode_text` only. The LLM-side helpers
(rewrite / generate) will land in Phase X-4.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


# ── 상수 ────────────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"
EMBEDDING_DIMENSIONS = 768

# ThreadPool 크기 — CPU 바운드 encode를 동시 2건까지 병렬화.
# GIL은 PyTorch 내부 C++ 경계에서 풀리므로 실효 병렬성이 확보된다.
_POOL_SIZE = 2

# 한국어 의약품 용어 정규화 맵 — FastAPI 버전과 동일 계약 유지.
# 사용자가 '효능·효과' 처럼 붙여 쓴 쿼리를 공백으로 분리해 검색 품질을 높인다.
_TERM_NORMALIZATIONS: dict[str, str] = {
    "효능·효과": "효능 효과",
    "용법·용량": "용법 용량",
    "사용상의주의사항": "사용상 주의사항",
    "사용상주의사항": "사용상 주의사항",
    "약물상호작용": "약물 상호작용",
    "mg/kg": "mg per kg",
    "1일": "하루",
    "2회": "두번",
    "3회": "세번",
    "4회": "네번",
}


# ── 싱글톤 상태 (프로세스 라이프사이클) ─────────────────────────────
# RQ 는 매 job 마다 새 asyncio event loop 를 만들어 실행한다.
# ``asyncio.Lock`` 은 생성 시점의 루프에 바인딩되므로 두 번째 job 부터
# "attached to a different loop" 로 깨진다. 따라서 루프 비의존인
# ``threading.Lock`` 을 사용한다 — 모델 로드 자체가 blocking 이어서
# GIL/이벤트-루프 차단은 어차피 동일한 비용이다.
_model: SentenceTransformer | None = None
_pool: ThreadPoolExecutor | None = None
_init_lock: threading.Lock = threading.Lock()


def _get_pool() -> ThreadPoolExecutor:
    """ThreadPool 싱글톤 — 최초 호출 시 lazy 생성."""
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=_POOL_SIZE, thread_name_prefix="emb")
    return _pool


def _load_model_blocking() -> SentenceTransformer:
    """모델 로드 + warmup 의 실제 blocking 구간 — ThreadPool 에서 실행된다.

    `threading.Lock` 로 보호해 동시 첫 호출에서도 한 번만 로드된다.
    """
    global _model
    with _init_lock:
        if _model is not None:
            return _model
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        loaded = SentenceTransformer(EMBEDDING_MODEL_NAME)
        loaded.encode("warmup")
        _model = loaded
        logger.info("Embedding model ready (dim=%d)", EMBEDDING_DIMENSIONS)
    return _model


async def _ensure_model() -> SentenceTransformer:
    """모델 싱글톤 보장. 이벤트 루프를 막지 않기 위해 ThreadPool 로 오프로드."""
    if _model is not None:
        return _model
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_get_pool(), _load_model_blocking)


# ── 순수 함수 ─────────────────────────────────────────────────────


def _preprocess(text: str) -> str:
    """입력 텍스트를 임베딩 친화 형태로 정규화."""
    if not text:
        return ""
    cleaned = " ".join(text.strip().split())
    for original, normalized in _TERM_NORMALIZATIONS.items():
        cleaned = cleaned.replace(original, normalized)
    return cleaned


def _normalize(vector: list[float]) -> list[float]:
    """L2-정규화 — cosine similarity 검색 시 일관된 스케일 보장."""
    arr = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vector
    return (arr / norm).tolist()


# ── 공개 API ─────────────────────────────────────────────────────


async def encode_text(text: str) -> list[float]:
    """임베딩 핵심 함수.

    Args:
        text: 임베딩 대상 문자열. 빈 문자열이면 영벡터를 반환한다.

    Returns:
        768차원 L2-정규화 float 리스트.
    """
    if not text:
        return [0.0] * EMBEDDING_DIMENSIONS

    model = await _ensure_model()
    processed = _preprocess(text)
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(_get_pool(), model.encode, processed)
    return _normalize(raw.tolist())
