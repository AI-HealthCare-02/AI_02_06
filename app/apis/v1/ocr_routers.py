"""OCR API router module.

This module contains HTTP endpoints for OCR (Optical Character Recognition)
operations including image processing, medication extraction, and data confirmation.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.dependencies.security import get_current_account
from app.dtos.ocr import ConfirmMedicationRequest, OcrExtractResponse
from app.models.accounts import Account
from app.models.profiles import Profile, RelationType
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/ocr", tags=["AI Integration"])

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
# Maximum file size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


def get_ocr_service() -> OCRService:
    """Get OCR service instance for dependency injection.

    Returns:
        OCRService: OCR service instance.
    """
    return OCRService()


@router.post(
    "/extract",
    response_model=OcrExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="[PHASE 1] Extract prescription image and temporary storage",
)
async def extract_medication_from_image(
    file: Annotated[UploadFile, File(description="Prescription/medicine bag image to recognize")],
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
) -> OcrExtractResponse:
    """Extract structured data from prescription image using OCR and LLM.

    Processes the image through OCR and LLM pipeline to extract structured data,
    then temporarily stores the result in Redis for security and returns a draft_id.

    Args:
        file: Uploaded prescription or medicine bag image file.
        ocr_service: OCR service instance.

    Returns:
        OcrExtractResponse: Extracted medication data with draft_id.

    Raises:
        HTTPException: If file format unsupported, file too large, or processing fails.
    """
    # Validate file format
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    # Validate file size
    # FastAPI's UploadFile provides size directly via .size attribute
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size too large. (Max: {MAX_FILE_SIZE // (1024 * 1024)}MB)",
        )

    # Reset file pointer to beginning before analysis
    await file.seek(0)

    try:
        # Call service
        result = await ocr_service.extract_and_parse_image(file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/draft/{draft_id}",
    response_model=OcrExtractResponse,
    summary="Get temporarily stored prescription data",
)
async def get_draft_medication(
    draft_id: str,
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
) -> OcrExtractResponse:
    """Safely retrieve data from frontend result page using draft_id.

    Args:
        draft_id: Draft ID for temporarily stored data.
        ocr_service: OCR service instance.

    Returns:
        OcrExtractResponse: Retrieved prescription data.

    Raises:
        HTTPException: If draft data expired or not found.
    """
    draft_data = await ocr_service.get_draft_data(draft_id)
    if not draft_data:
        raise HTTPException(status_code=404, detail="Expired or non-existent data.")
    return draft_data


@router.post(
    "/confirm",
    status_code=status.HTTP_201_CREATED,
    summary="[PHASE 3] Save modified prescription data to DB and generate guide",
)
async def confirm_and_save_medication(
    request: ConfirmMedicationRequest,
    background_tasks: BackgroundTasks,
    ocr_service: Annotated[OCRService, Depends(get_ocr_service)],
    current_account: Annotated[Account, Depends(get_current_account)],
) -> dict:
    """Save finalized medication list from frontend to DB and return medication guide.

    Args:
        request: Confirmation request with finalized medication data.
        ocr_service: OCR service instance.
        current_account: Current authenticated account.

    Returns:
        dict: Response with saved medications and generated guide.

    Raises:
        HTTPException: If user profile not found or processing fails.
    """
    # Find logged-in account's 'SELF' profile
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
        result = await ocr_service.confirm_and_save(request, str(profile.id), background_tasks)
        return result
    except Exception as e:
        # Print full error details to terminal in red
        import traceback

        print("\n" + "=" * 50)
        print("🚨 Backend 500 error occurred! Detailed log:")
        traceback.print_exc()
        print("=" * 50 + "\n")

        # Send detailed content to frontend response (Network tab)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backend Error: {e!s} | Trace: {traceback.format_exc()}",
        ) from e
