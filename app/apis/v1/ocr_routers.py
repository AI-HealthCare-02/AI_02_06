import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.queues.rq import get_queue
from app.services.ocr_service import _UPLOAD_DIR, OCRService

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
    status_code=status.HTTP_202_ACCEPTED,
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
    # Note: UploadFile은 tell()/whence seek()가 타입/버전별로 흔들리므로, read()로 size를 계산합니다.
    data = await file.read()
    file_size = len(data)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "error_description": f"파일 크기가 너무 큽니다. (최대: {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            }
        )

    try:
        safe_name = Path(file.filename or "upload").name
        image_path = _UPLOAD_DIR / f"{uuid.uuid4()}_{safe_name}"
        with image_path.open("wb") as f:
            f.write(data)

        q = get_queue("ai")
        job = q.enqueue(
            "ai_worker.tasks.ocr_tasks.run_ocr_from_path",
            str(image_path),
            original_filename=file.filename,
            job_timeout=120,
        )
        return {"job_id": job.id, "status": "queued"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
