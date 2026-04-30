"""Lifestyle guide API router module.

라우팅 흐름은 OCR 와 동일한 RQ producer + SSE long-poll 패턴을 따른다:

1. ``POST /lifestyle-guides/generate`` -> 202 Accepted + pending guide_id
2. ``GET  /lifestyle-guides/{guide_id}/stream`` -> SSE (status 변화 push)
3. ``GET  /lifestyle-guides/{guide_id}`` -> 단발 폴링 (legacy 호환)
4. 기타 list/latest/delete/challenges 는 기존과 동일.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.dependencies.security import get_current_account
from app.dtos.challenge import ChallengeResponse
from app.dtos.lifestyle_guide import LifestyleGuidePendingResponse, LifestyleGuideResponse
from app.models.accounts import Account
from app.services.lifestyle_guide_service import LifestyleGuideService

router = APIRouter(prefix="/lifestyle-guides", tags=["Lifestyle Guides"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # nginx 가 SSE chunk 를 buffer 하지 않도록
}


def get_lifestyle_guide_service() -> LifestyleGuideService:
    """LifestyleGuideService 인스턴스 (DI)."""
    return LifestyleGuideService()


# Type aliases for dependency injection
LifestyleGuideServiceDep = Annotated[LifestyleGuideService, Depends(get_lifestyle_guide_service)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


# ── POST /lifestyle-guides/generate (RQ enqueue) ─────────────────────────
# 흐름: ownership 검증 -> 활성 약물 snapshot -> pending row INSERT
#       -> RQ enqueue -> 202 + pending guide_id
@router.post(
    "/generate",
    response_model=LifestyleGuidePendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue lifestyle guide generation (async)",
)
async def enqueue_guide(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuidePendingResponse:
    """라이프스타일 가이드 생성을 비동기로 시작한다.

    LLM 호출은 ai-worker 가 수행하므로 이 엔드포인트는 즉시 반환한다.
    프론트는 응답 ``id`` 로 ``GET /lifestyle-guides/{id}/stream`` SSE 를 연다.

    Args:
        profile_id: 가이드 받을 프로필 UUID.
        current_account: 인증된 계정.
        service: 라이프스타일 가이드 서비스.

    Returns:
        ``LifestyleGuidePendingResponse`` — pending guide id + status.

    Raises:
        HTTPException 409: 활성 약물(복용 중인 처방약) 미등록 시 — service
            가 직접 raise. 응답 ``detail`` 에 ``code=NO_ACTIVE_MEDICATIONS`` /
            ``message`` (사용자 안내) / ``redirect_to=/ocr`` 가 포함되어
            FE 가 토스트 표시 + 처방전 등록 페이지 라우팅을 한 번에 처리한다.
    """
    guide = await service.enqueue_guide_with_owner_check(profile_id, current_account.id)
    # Phase B dedupe hit 이면 service 가 이미 ready 가이드를 반환 — status 도
    # 함께 응답해 FE 가 SSE 를 건너뛰고 즉시 GET 으로 fetch 할 수 있게 한다.
    return LifestyleGuidePendingResponse(id=guide.id, status=guide.status)


# ── GET /lifestyle-guides/{guide_id}/stream (SSE long-poll) ──────────────
# 흐름: ownership 은 stream 내부에서 검증 -> StreamingResponse 즉시 반환
@router.get(
    "/{guide_id}/stream",
    summary="라이프스타일 가이드 SSE 스트림 (status 변화만 push)",
)
async def stream_guide(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> StreamingResponse:
    """SSE 로 가이드 생성 진행 상태를 push 한다.

    이벤트:

    - ``update`` : status 변화 시 (첫 호출은 즉시 1회). data = LifestyleGuideResponse JSON.
    - ``timeout``: 단일 연결 max_seconds 초과 시. 클라이언트가 재연결.
    - ``error`` : guide 가 사라졌거나 ownership 위반.
    """
    return StreamingResponse(
        service.stream_guide_states(guide_id, current_account.id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get(
    "/latest",
    response_model=LifestyleGuideResponse,
    summary="Get latest lifestyle guide",
)
async def get_latest_guide(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuideResponse:
    """프로필의 가장 최근 가이드 (status 무관)."""
    guide = await service.get_latest_guide_with_owner_check(profile_id, current_account.id)
    return LifestyleGuideResponse.model_validate(guide)


@router.get(
    "",
    response_model=list[LifestyleGuideResponse],
    summary="List lifestyle guides",
)
async def list_guides(
    profile_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> list[LifestyleGuideResponse]:
    """프로필의 모든 가이드를 newest-first 로 반환."""
    guides = await service.list_guides_with_owner_check(profile_id, current_account.id)
    return [LifestyleGuideResponse.model_validate(g) for g in guides]


@router.get(
    "/{guide_id}",
    response_model=LifestyleGuideResponse,
    summary="Get lifestyle guide details",
)
async def get_guide(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> LifestyleGuideResponse:
    """단발 폴링 — SSE 안 쓰고 한 번만 status/content 를 받고 싶을 때."""
    guide = await service.get_guide_with_owner_check(guide_id, current_account.id)
    return LifestyleGuideResponse.model_validate(guide)


@router.delete(
    "/{guide_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lifestyle guide",
)
async def delete_guide(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> None:
    """가이드 삭제. 활성/완료 챌린지는 보존(guide_id=None), 미시작 챌린지는 soft delete."""
    await service.delete_guide_with_owner_check(guide_id, current_account.id)


@router.get(
    "/{guide_id}/challenges",
    response_model=list[ChallengeResponse],
    summary="List guide challenges",
)
async def get_guide_challenges(
    guide_id: UUID,
    current_account: CurrentAccount,
    service: LifestyleGuideServiceDep,
) -> list[ChallengeResponse]:
    """해당 가이드에서 만들어진 챌린지 목록."""
    challenges = await service.get_guide_challenges_with_owner_check(guide_id, current_account.id)
    return [ChallengeResponse.model_validate(c) for c in challenges]
