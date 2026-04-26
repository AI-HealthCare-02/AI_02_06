"""OCR API router module.

본 라우터는 HTTP I/O 만 담당한다. CLOVA OCR 호출과 약품 매칭은
ai-worker 의 ``process_ocr_task`` 가 비동기로 처리하며, FastAPI 는
업로드 bytes 를 RQ 에 enqueue 하고 draft_id 를 즉시 반환한다.

흐름:
1. ``POST /ocr/extract`` -> 즉시 200 + draft_id (medicines=[])
2. ``GET  /ocr/draft/{id}`` -> status (pending/ready/no_text/...) + medicines
3. ``POST /ocr/confirm`` -> DB 영구 저장
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies.security import get_current_account
from app.dtos.ocr import (
    ConfirmMedicationRequest,
    OcrDraftPollResponse,
    OcrExtractResponse,
)
from app.models.accounts import Account
from app.models.profiles import Profile, RelationType
from app.services.ocr_service import OCRService

# 라우터 전역 인증 게이트 — 모든 OCR 엔드포인트는 로그인된 계정만 사용 가능.
# extract / draft 는 결과 객체를 쓰지 않아 ``dependencies`` 로 주입하지 않고
# 게이트만 걸고, confirm 은 함수 시그니처에서 ``current_account`` 를 받아 사용.
router = APIRouter(
    prefix="/ocr",
    tags=["AI Integration"],
    dependencies=[Depends(get_current_account)],
)

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def get_ocr_service() -> OCRService:
    """OCRService 인스턴스를 반환 (의존성 주입용)."""
    return OCRService()


@router.post(
    "/extract",
    response_model=OcrExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="처방전 이미지 업로드 후 OCR 비동기 처리 시작",
)
async def extract_medication_from_image(
    file: Annotated[UploadFile, File(description="Prescription/medicine bag image to recognize")],
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
) -> OcrExtractResponse:
    """이미지를 ai-worker 로 enqueue 하고 draft_id 를 즉시 반환한다.

    실제 OCR 처리는 ai-worker 의 RQ task 가 비동기로 수행한다. 프론트는
    응답으로 받은 ``draft_id`` 로 ``/ocr/draft/{id}`` 를 폴링해 결과를 회수한다.

    Args:
        file: 업로드된 처방전/약봉투 이미지 파일.
        ocr_service: OCR 서비스 인스턴스.

    Returns:
        ``OcrExtractResponse`` — ``draft_id`` 와 빈 ``medicines`` 리스트.

    Raises:
        HTTPException: 형식 미지원·크기 초과·파일 누락.
    """
    _validate_upload(file)
    await file.seek(0)
    return await ocr_service.enqueue_ocr_task(file)


def _validate_upload(file: UploadFile) -> None:
    """업로드 파일의 형식·크기를 검증한다."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file format.")
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size too large. (Max: {MAX_FILE_SIZE // (1024 * 1024)}MB)",
        )


@router.get(
    "/draft/{draft_id}",
    response_model=OcrDraftPollResponse,
    summary="OCR 처리 결과 폴링 (status + medicines)",
)
async def get_draft_medication(
    draft_id: str,
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
) -> OcrDraftPollResponse:
    """폴링 — ai-worker 의 처리 상태를 종합해 반환한다.

    응답의 ``status`` 가 ``pending`` 이면 프론트는 다시 폴링해야 하고,
    ``ready`` 면 ``medicines`` 가 채워져 있다. 그 외(``no_text``,
    ``no_candidates``, ``failed``)는 사용자에게 안내 메시지를 보여준다.

    Args:
        draft_id: enqueue 응답의 draft_id.
        ocr_service: OCR 서비스 인스턴스.

    Returns:
        ``OcrDraftPollResponse``.
    """
    return await ocr_service.get_draft_data(draft_id)


@router.post(
    "/confirm",
    status_code=status.HTTP_201_CREATED,
    summary="검수 완료 약품 메타를 DB 에 영구 저장",
)
async def confirm_and_save_medication(
    request: ConfirmMedicationRequest,
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
    current_account: Annotated[Account, Depends(get_current_account)],
) -> dict:
    """사용자가 검수·수정한 최종 약품 리스트를 DB 에 저장한다.

    Args:
        request: 검수 완료된 약품 리스트와 draft_id.
        ocr_service: OCR 서비스 인스턴스.
        current_account: 현재 인증된 계정.

    Returns:
        ``{"status": "success", "message": "N개 저장"}``.

    Raises:
        HTTPException: 프로필 없음 또는 처리 실패.
    """
    profile = await Profile.filter(
        account_id=current_account.id,
        relation_type=RelationType.SELF,
        deleted_at__isnull=True,
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connected user profile information not found.",
        )

    try:
        return await ocr_service.confirm_and_save(request, str(profile.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
