"""Image preprocessing module for OCR optimization.

This module provides OpenCV-based image preprocessing pipeline
to enhance prescription bag images before CLOVA OCR processing.

Reference:
    - OpenCV 4.x adaptive thresholding (2024)
    - Korean prescription OCR preprocessing best practices
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_for_ocr(image_path: str) -> str:
    """Apply full preprocessing pipeline for OCR optimization.

    Processes the input image through grayscale conversion,
    Gaussian blur denoising, adaptive thresholding, and
    morphological operations to improve OCR accuracy.

    Args:
        image_path: Path to the original image file.

    Returns:
        Path to the preprocessed image file.

    Raises:
        FileNotFoundError: If the input image does not exist.
        ValueError: If the image cannot be loaded.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")

    gray = _to_grayscale(image)
    blurred = _denoise(gray)
    binary = _adaptive_threshold(blurred)
    cleaned = _morphology_clean(binary)

    output_path = path.parent / f"{path.stem}_preprocessed{path.suffix}"
    cv2.imwrite(str(output_path), cleaned)

    logger.info("Preprocessed image saved: %s", output_path)
    return str(output_path)


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale.

    Args:
        image: Input BGR image array.

    Returns:
        Grayscale image array.
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _denoise(gray: np.ndarray) -> np.ndarray:
    """Apply Gaussian blur to reduce noise.

    Uses a 5x5 kernel for moderate noise reduction
    while preserving text edges in prescription images.

    Args:
        gray: Grayscale image array.

    Returns:
        Denoised image array.
    """
    return cv2.GaussianBlur(gray, (5, 5), 0)


def _adaptive_threshold(blurred: np.ndarray) -> np.ndarray:
    """Apply adaptive thresholding for uneven lighting.

    Uses Gaussian-weighted adaptive thresholding to handle
    varying illumination across prescription bag photographs.

    Args:
        blurred: Denoised grayscale image array.

    Returns:
        Binary image array.
    """
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        8,
    )


def _morphology_clean(binary: np.ndarray) -> np.ndarray:
    """Apply morphological operations to clean binary image.

    Uses dilation followed by erosion (closing) to connect
    broken character strokes and remove small noise artifacts.

    Args:
        binary: Binary image array from thresholding.

    Returns:
        Cleaned binary image array.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(binary, kernel, iterations=1)
    return cv2.erode(dilated, kernel, iterations=1)
