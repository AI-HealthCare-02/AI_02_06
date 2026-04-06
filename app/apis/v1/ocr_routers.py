from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.services.ocr_service import OCRService

router = APIRouter(prefix="/ocr", tags=["AI Integration"])


def get_ocr_service() -> OCRService:
    """OCRService 의존성 주입을 위한 팩토리 함수"""
    return OCRService()


@router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="이미지 업로드 및 OCR 추출",
    description="사용자가 업로드한 처방전 이미지를 바탕으로 약품 정보를 추출합니다."
)
async def upload_image_for_ocr(
    file: Annotated[UploadFile, File(description="인식할 처방전/약봉투 이미지")],
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)]
):
    """
    프론트엔드에서 전달된 파일을 받아 OCR 분석 후 결과를 반환합니다.
    """
    result = await ocr_service.extract_text_from_image(file)
    return result
