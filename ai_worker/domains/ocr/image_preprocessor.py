"""처방전 이미지 OCR 전처리.

CLOVA OCR API 에 보내기 전 이미지 품질을 개선하는 OpenCV 파이프라인.
처방봉투 사진 특유의 조명 불균일·노이즈·끊긴 글자 등을 보정한다.

흐름: 원본 로드 -> 그레이스케일 -> 가우시안 블러 -> 적응형 이진화
       -> 모폴로지 클로징 -> 디스크 저장
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_for_ocr(image_path: str) -> str:
    """이미지를 OCR 친화 포맷으로 변환해 디스크에 저장한다.

    Args:
        image_path: 원본 이미지 파일 경로.

    Returns:
        전처리된 이미지 파일 경로 (``{원본}_preprocessed.{ext}``).

    Raises:
        FileNotFoundError: 원본 파일이 없을 때.
        ValueError: 이미지 디코딩 실패.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")

    cleaned = _run_pipeline(image)
    output_path = path.parent / f"{path.stem}_preprocessed{path.suffix}"
    cv2.imwrite(str(output_path), cleaned)
    logger.info("Preprocessed image saved: %s", output_path)
    return str(output_path)


def _run_pipeline(image: np.ndarray) -> np.ndarray:
    """4단계 전처리를 순차 적용한다."""
    gray = _to_grayscale(image)
    blurred = _denoise(gray)
    binary = _adaptive_threshold(blurred)
    return _morphology_clean(binary)


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """BGR 이미지를 그레이스케일로 변환."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _denoise(gray: np.ndarray) -> np.ndarray:
    """5x5 가우시안 블러로 노이즈 완화 (글자 엣지는 보존)."""
    return cv2.GaussianBlur(gray, (5, 5), 0)


def _adaptive_threshold(blurred: np.ndarray) -> np.ndarray:
    """가우시안 가중 적응형 이진화로 조명 불균일을 보정."""
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        8,
    )


def _morphology_clean(binary: np.ndarray) -> np.ndarray:
    """팽창 → 침식(클로징) 으로 끊긴 글자를 잇고 작은 노이즈를 제거."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(binary, kernel, iterations=1)
    return cv2.erode(dilated, kernel, iterations=1)
