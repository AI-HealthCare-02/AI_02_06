"""Tool-calling RQ jobs — RAG 4단 파이프라인.

진입점:
- ``run_tool_calls_job(calls)``  — 한 턴의 모든 tool_calls 를 ``asyncio.gather``
  로 병행 실행, ``{tool_call_id: result}`` 반환.

Router LLM (route_intent_job) 은 폐기 — IntentClassifier (4o-mini) 가
FastAPI 측에서 직접 호출. 본 jobs 파일은 fan-out 으로 만든
search_medicine_knowledge_base x N 호출만 담당.

Tortoise lifecycle: RAG retrieval tool (``search_medicine_knowledge_base``)
은 medicine_chunk DB 쿼리 필요 → ``run_tool_calls_job`` 이 호출 시작 시
Tortoise.init, 종료 시 close_connections 한 번 묶어 처리. RAG 호출 없으면
lifecycle 스킵 (위치 검색만 도는 turn 의 DB 연결 비용 0).
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from tortoise import Tortoise

from ai_worker.domains.rag.retrieval import retrieve_medicine_chunks
from app.db.databases import TORTOISE_ORM
from app.dtos.tools import KakaoPlace
from app.services.rag.openai_embedding import encode_queries_batch
from app.services.tools.maps.hospital_search import (
    DEFAULT_RADIUS_M,
    HospitalCategory,
    search_hospitals_by_keyword,
    search_hospitals_by_location,
)
from app.services.tools.recalls.checker import (
    check_manufacturer_recalls,
    check_user_medications_recall,
)
from app.services.tools.retry import retry_async

logger = logging.getLogger(__name__)

_CATEGORY_TO_ENUM: dict[str, HospitalCategory] = {
    "약국": HospitalCategory.PHARMACY,
    "병원": HospitalCategory.HOSPITAL,
}

_MEDICINE_KNOWLEDGE_TOOL_NAME = "search_medicine_knowledge_base"


# ── tool_calls 병렬 dispatch (RQ Task) ──────────────────────────────
# 흐름: 빈 calls 단축 -> RAG 포함 여부에 따라 Tortoise lifecycle
#       -> RAG 쿼리 batch 임베딩 사전 계산 (1회 OpenAI API 호출)
#       -> asyncio.gather 로 dispatch 병행 (사전계산 임베딩 주입)
#       -> 결과 merge -> lifecycle close
async def run_tool_calls_job(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """[RQ Task] 모든 tool_call 을 병행 실행해 ``{tool_call_id: result}`` 반환.

    Args:
        calls: 각 dict 가 ``tool_call_id``, ``name``, ``arguments`` 보유.
            location 호출은 ``geolocation: {lat, lng}`` 도 필요.

    Returns:
        성공 결과는 ``{"places": [...]}`` (병원/약국) 또는
        ``{"chunks": [...]}`` (의학 지식), 실패는 ``{"error": str}``.

    Note:
        fan-out 으로 만들어진 search_medicine_knowledge_base x N 호출의
        쿼리들은 dispatch 진입 전 batch 임베딩 1회로 묶어 처리한다.
        OpenAI 임베딩 API 호출 N -> 1 (응답 속도 + 비용 최적화).
    """
    if not calls:
        return {}

    _log_run_start(calls)
    needs_db = _needs_tortoise(calls)
    if needs_db:
        await Tortoise.init(config=TORTOISE_ORM)
    try:
        embeddings_by_call_id = await _batch_embed_rag_queries(calls)
        results = await asyncio.gather(
            *[_dispatch(call, embeddings_by_call_id) for call in calls],
            return_exceptions=False,
        )
    finally:
        if needs_db:
            await Tortoise.close_connections()
    merged = {call["tool_call_id"]: result for call, result in zip(calls, results, strict=True)}
    _log_run_done(merged)
    return merged


def _needs_tortoise(calls: list[dict[str, Any]]) -> bool:
    """``calls`` 안에 DB 접근이 필요한 tool 이 하나라도 있는지."""
    return any(call.get("name") == _MEDICINE_KNOWLEDGE_TOOL_NAME for call in calls)


# ── fan-out 쿼리 batch 임베딩 (OpenAI N→1 최적화) ─────────────────────
# 흐름: search_medicine_knowledge_base 호출 추출 -> query 추출
#       -> encode_queries_batch 1회 호출 -> tool_call_id ↔ embedding 매핑
async def _batch_embed_rag_queries(calls: list[dict[str, Any]]) -> dict[str, list[float]]:
    """RAG 검색 쿼리들을 1회 batch 호출로 임베딩한다.

    Returns:
        ``{tool_call_id: embedding}`` 매핑. RAG 호출이 없으면 빈 dict.
        빈 query 가 섞여 있어도 batch 응답 순서가 보장되므로 그대로 매핑.
    """
    rag_calls = [c for c in calls if c.get("name") == _MEDICINE_KNOWLEDGE_TOOL_NAME]
    if not rag_calls:
        return {}

    queries = [(c.get("arguments") or {}).get("query", "").strip() for c in rag_calls]
    embeddings = await encode_queries_batch(queries)
    logger.info("[ToolCalling] batch embed: %d queries -> 1 OpenAI call", len(queries))
    return {call["tool_call_id"]: embedding for call, embedding in zip(rag_calls, embeddings, strict=True)}


def _log_run_start(calls: list[dict[str, Any]]) -> None:
    """병렬 호출 시작 로그."""
    logger.info(
        "[ToolCalling] run_tool_calls_job start calls=%d names=%s",
        len(calls),
        ",".join(c.get("name", "?") for c in calls),
    )


def _log_run_done(merged: dict[str, dict[str, Any]]) -> None:
    """병렬 호출 종료 로그 (성공/실패 카운트)."""
    error_count = sum(1 for r in merged.values() if "error" in r)
    logger.info("[ToolCalling] run_tool_calls_job done ok=%d errors=%d", len(merged) - error_count, error_count)


async def _dispatch(
    call: dict[str, Any],
    embeddings_by_call_id: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """단일 call dict 를 적절한 함수로 라우팅. 예외는 결과 dict 로 직렬화.

    Args:
        call: tool_call dict (``tool_call_id``, ``name``, ``arguments`` ...).
        embeddings_by_call_id: ``run_tool_calls_job`` 이 사전 batch 임베딩한
            ``{tool_call_id: embedding}`` 매핑. RAG 호출이 본 매핑에 있으면
            OpenAI 임베딩 API skip.
    """
    name = call.get("name", "")
    try:
        if name == "search_hospitals_by_keyword":
            return await _run_keyword(call)
        if name == "search_hospitals_by_location":
            return await _run_location(call)
        if name == _MEDICINE_KNOWLEDGE_TOOL_NAME:
            return await _run_medicine_knowledge(call, embeddings_by_call_id or {})
        if name == "check_user_medications_recall":
            return await _run_user_recall(call)
        if name == "check_manufacturer_recalls":
            return await _run_manufacturer_recall(call)
    except Exception as exc:
        logger.exception("[ToolCalling] tool call %r failed", name)
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"error": f"unknown function: {name}"}


async def _run_medicine_knowledge(
    call: dict[str, Any],
    embeddings_by_call_id: dict[str, list[float]],
) -> dict[str, Any]:
    """RAG retrieval 을 실행한다 (Tortoise lifecycle 은 호출자가 관리).

    호출자가 batch 임베딩한 결과가 ``embeddings_by_call_id`` 에 있으면
    그것을 그대로 retrieve_medicine_chunks 에 주입 — OpenAI 임베딩 API
    개별 호출 (N→1) 절약.
    """
    arguments = call.get("arguments") or {}
    query = arguments.get("query", "")
    precomputed = embeddings_by_call_id.get(call.get("tool_call_id", ""))
    return await retrieve_medicine_chunks(query=query, precomputed_embedding=precomputed)


# Kakao API 외부 호출은 retry decorator 적용 — 일시적 ConnectionError /
# TimeoutError 시 자동 재시도. PLAN.md (feature/RAG) §4 D1 결정.
@retry_async()
async def _kakao_keyword(query: str) -> list[KakaoPlace]:
    return await search_hospitals_by_keyword(query=query)


@retry_async()
async def _kakao_location(
    *,
    lat: float,
    lng: float,
    radius_m: int,
    category: HospitalCategory,
) -> list[KakaoPlace]:
    return await search_hospitals_by_location(lat=lat, lng=lng, radius_m=radius_m, category=category)


async def _run_keyword(call: dict[str, Any]) -> dict[str, Any]:
    """키워드 기반 병원/약국 검색을 실행한다 (Kakao API + retry)."""
    arguments = call.get("arguments") or {}
    query = arguments.get("query", "")
    places = await _kakao_keyword(query=query)
    return {"places": _places_to_dict_list(places)}


async def _run_location(call: dict[str, Any]) -> dict[str, Any]:
    """위치 기반 병원/약국 검색을 실행한다 (Kakao API + retry, geolocation 필수)."""
    geolocation = call.get("geolocation")
    if not _is_valid_geolocation(geolocation):
        return {"error": "missing geolocation: location tool requires lat/lng in call payload"}

    arguments = call.get("arguments") or {}
    category = _CATEGORY_TO_ENUM.get(arguments.get("category", "약국"), HospitalCategory.PHARMACY)
    radius_m = int(arguments.get("radius_m", DEFAULT_RADIUS_M))
    places = await _kakao_location(
        lat=float(geolocation["lat"]),
        lng=float(geolocation["lng"]),
        radius_m=radius_m,
        category=category,
    )
    return {"places": _places_to_dict_list(places)}


def _is_valid_geolocation(geolocation: dict[str, Any] | None) -> bool:
    """Geolocation dict 가 lat/lng 를 실제 숫자값으로 가졌는지 검증.

    이전에는 키 존재만 확인해 ``{"lat": None, "lng": None}`` 같은 케이스가
    통과 -> Kakao API 호출 단계에서 ValueError. 호출 전 차단으로 의미 있는
    에러 메시지 제공.
    """
    if not geolocation:
        return False
    lat = geolocation.get("lat")
    lng = geolocation.get("lng")
    return isinstance(lat, (int, float)) and isinstance(lng, (int, float))


def _places_to_dict_list(places: list[KakaoPlace]) -> list[dict[str, Any]]:
    """KakaoPlace 리스트를 RQ pickle 안전한 dict 리스트로 변환."""
    return [p.model_dump() for p in places]


# ── 회수·판매중지 툴 dispatch (Phase 7) ─────────────────────────────
# 흐름: call.profile_id 추출 -> checker 호출 -> 응답 dict 그대로 반환
# call payload 는 백엔드 _dispatch_tool_calls 가 profile_id 를 주입.


def _resolve_profile_id(call: dict[str, Any]) -> UUID:
    """Call payload 에서 profile_id 를 UUID 로 변환."""
    raw = call.get("profile_id")
    if raw is None:
        msg = "missing profile_id: recall tool requires profile_id in call payload"
        raise ValueError(msg)
    return raw if isinstance(raw, UUID) else UUID(str(raw))


async def _run_user_recall(call: dict[str, Any]) -> dict[str, Any]:
    """Q1 — 사용자 복용약 회수 매칭 실행."""
    profile_id = _resolve_profile_id(call)
    return await check_user_medications_recall(profile_id=profile_id)


async def _run_manufacturer_recall(call: dict[str, Any]) -> dict[str, Any]:
    """Q2 — 제조사 회수 매칭 실행."""
    profile_id = _resolve_profile_id(call)
    arguments = call.get("arguments") or {}
    manufacturer = arguments.get("manufacturer") or None
    return await check_manufacturer_recalls(profile_id=profile_id, manufacturer=manufacturer)
