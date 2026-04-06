import asyncio
from typing import Any

from fastapi import UploadFile


class OCRService:
    """
    OCR (광학 문자 인식) 서비스
    처방전 및 약봉투 이미지에서 약품 정보를 추출합니다.
    """

    async def extract_text_from_image(self, file: UploadFile) -> dict[str, Any]:
        """
        이미지 파일에서 텍스트 및 약품 정보를 추출합니다.
        현재는 Mock 데이터를 반환하며, 추후 AI 모델(Tesseract, Google Vision 등) 연동 예정입니다.
        """
        # 파일 읽기 시뮬레이션
        _content = await file.read()
        
        # 실제 AI 모델 추론 처리를 위한 지연 시간 시뮬레이션 (1초)
        await asyncio.sleep(1)

        # Mock 추출 결과
        mock_result = {
            "status": "success",
            "filename": file.filename,
            "detected_items": [
                {
                    "medicine_name": "타이레놀정 500mg",
                    "dose_per_intake": "1정",
                    "intake_times": ["08:00", "13:00", "18:00"],
                    "total_days": 3,
                    "instruction": "식후 30분 복용"
                },
                {
                    "medicine_name": "아모디핀정",
                    "dose_per_intake": "0.5정",
                    "intake_times": ["08:00"],
                    "total_days": 30,
                    "instruction": "아침 식사 전 복용"
                }
            ],
            "raw_text": "추출된 전체 텍스트 내역 (OCR 원본 데이터)..."
        }

        return mock_result
