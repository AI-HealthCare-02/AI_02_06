"""ko-sroberta SentenceTransformer 임베딩 — ai-worker 프로세스 싱글톤.

heavy weights (~420MB) 를 단 한 번만 로드해서 모든 RQ job 이 재사용한다.
FastAPI 는 ``embed_text_job`` 을 enqueue 하기만 하므로 모델은 워커 쪽
프로세스에만 상주한다.

설계 메모:
- 모델 로드는 ~30초 / blocking → ThreadPool 로 오프로드해 이벤트루프 비차단
- ``encode`` 는 PyTorch C++ 내부에서 GIL 을 풀어주므로 ThreadPool 병렬 효율 OK
- ``threading.Lock`` 사용 — RQ 가 매 job 마다 새 event loop 를 만들어 ``asyncio.Lock``
  은 "attached to a different loop" 로 깨지므로 루프 비의존인 lock 이 안전
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"
EMBEDDING_DIMENSIONS = 768
_POOL_SIZE = 2

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
    """모델 로드 + warmup 의 실제 blocking 구간 (ThreadPool 에서 실행)."""
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
    """모델 싱글톤 보장 — 이벤트 루프를 막지 않기 위해 ThreadPool 오프로드."""
    if _model is not None:
        return _model
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_get_pool(), _load_model_blocking)


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


async def encode_text(text: str) -> list[float]:
    """문자열 1개를 768차원 L2-정규화 임베딩 벡터로 변환한다.

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
