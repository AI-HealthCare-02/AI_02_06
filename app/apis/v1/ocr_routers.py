from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

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
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="이미지 업로드 및 OCR 추출",
    description="사용자가 업로드한 처방전 이미지를 바탕으로 약품 정보를 추출합니다. (JPG, PNG, WEBP 지원, 최대 5MB)"
)
async def upload_image_for_ocr(
    file: Annotated[UploadFile, File(description="인식할 처방전/약봉투 이미지")],
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)]
):
    """
    프론트엔드에서 전달된 파일을 받아 유효성 검사 후 OCR 분석 결과를 반환합니다.
    """
    # 1. 파일 형식 검증
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_file_type",
                "error_description": f"지원하지 않는 파일 형식입니다. (허용: {', '.join(ALLOWED_IMAGE_TYPES)})"
            }
        )

    # 2. 파일 크기 검증
    # Note: 파일 크기를 확인하기 위해 포인터를 끝으로 이동시킵니다.
    await file.seek(0, 2)
    file_size = await file.tell()
    await file.seek(0)  # 다시 처음으로 되돌림

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "error_description": f"파일 크기가 너무 큽니다. (최대: {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            }
        )

    result = await ocr_service.extract_text_from_image(file)
    return result
