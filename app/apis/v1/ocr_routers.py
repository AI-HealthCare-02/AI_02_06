from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies.security import get_current_account
from app.dtos.ocr import ConfirmMedicationRequest, OcrExtractResponse
from app.models.accounts import Account
from app.models.profiles import Profile, RelationType
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/ocr", tags=["AI Integration"])

# 허용되는 이미지 MIME 타입
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
# 최대 파일 크기 (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


def get_ocr_service() -> OCRService:
    """OCRService 의존성 주입을 위한 팩토리 함수"""
    return OCRService()


@router.post(
    "/extract",
    response_model=OcrExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="[PHASE 1] 처방전 이미지 추출 및 임시 저장",
)
async def extract_medication_from_image(
    file: Annotated[UploadFile, File(description="인식할 처방전/약봉투 이미지")],
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
):
    """
    이미지를 받아 OCR과 LLM을 거쳐 구조화된 데이터를 추출하고,
    보안을 위해 결과를 Redis에 임시 저장한 뒤 draft_id를 반환합니다.
    """
    # 1. 파일 형식 검증 (기존 코드 유지)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    # 2. 파일 크기 검증 (에러 유발하는 seek(0, 2)와 tell() 삭제)
    # FastAPI의 UploadFile은 .size 속성을 통해 크기를 직접 제공합니다.
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail=f"파일 크기가 너무 큽니다. (최대: {MAX_FILE_SIZE // (1024 * 1024)}MB)"
        )

    # 💡 중요: 분석 전 파일 포인터를 맨 앞으로 초기화 (인자 하나만 전달)
    await file.seek(0)

    try:
        # 서비스 호출
        result = await ocr_service.extract_and_parse_image(file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/draft/{draft_id}", response_model=OcrExtractResponse, summary="임시 저장된 처방전 데이터 조회")
async def get_draft_medication(draft_id: str, ocr_service: Annotated[OCRService, Depends(get_ocr_service)]):
    """프론트엔드 결과 페이지에서 draft_id를 통해 데이터를 안전하게 불러옵니다."""
    draft_data = await ocr_service.get_draft_data(draft_id)
    if not draft_data:
        raise HTTPException(status_code=404, detail="만료되었거나 존재하지 않는 데이터입니다.")
    return draft_data


@router.post(
    "/confirm", status_code=status.HTTP_201_CREATED, summary="[PHASE 3] 수정된 처방전 데이터 DB 저장 및 가이드 생성"
)
async def confirm_and_save_medication(
    request: ConfirmMedicationRequest,
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
    current_account: Annotated[Account, Depends(get_current_account)],
):
    """
    프론트엔드에서 최종 확정한 약품 리스트를 받아 DB에 저장하고,
    완성된 복약 가이드를 반환합니다.
    """

    # 💡 로그인한 계정의 '본인(SELF)' 프로필 조회
    profile = await Profile.filter(
        account_id=current_account.id, relation_type=RelationType.SELF, deleted_at__isnull=True
    ).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연결된 본인 프로필 정보를 찾을 수 없습니다.")

    try:
        result = await ocr_service.confirm_and_save(request, str(profile.id))
        return result
    # except Exception as e:
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    except Exception as e:
        # ✅ 터미널에 에러 전체 내용을 빨간 글씨로 다 찍어버립니다.
        import traceback

        print("\n" + "=" * 50)
        print("🚨 백엔드 500 에러 발생! 상세 로그:")
        traceback.print_exc()
        print("=" * 50 + "\n")

        # ✅ 프론트엔드 응답(Network 탭)에도 상세 내용을 실어 보냅니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backend Error: {str(e)} | Trace: {traceback.format_exc()}",
        ) from e
