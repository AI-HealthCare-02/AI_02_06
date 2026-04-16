import json
import os
import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import redis.asyncio as redis
from fastapi import UploadFile
from rq import Queue
from redis import Redis

from app.dtos.ocr import ConfirmMedicationRequest, ExtractedMedicine, OcrExtractResponse
from app.models.medication import Medication
from app.core.config import config

# 공유 볼륨 경로 (Docker Compose의 ai-worker와 공유되어야 함)
_UPLOAD_DIR = Path(os.environ.get("ALLOWED_IMAGE_DIR", tempfile.gettempdir())) / "ocr_images"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class OCRService:
    def __init__(self) -> None:
        # 비동기 Redis (API 응답용)
        self.redis = redis.from_url(config.REDIS_URL, decode_responses=True)
        
        # 동기 Redis & RQ Queue (워커 위임용)
        self.sync_redis = Redis.from_url(config.REDIS_URL)
        self.queue = Queue("ai", connection=self.sync_redis)

    async def extract_and_parse_image(self, file: UploadFile) -> dict[str, str]:
        """
        이미지를 저장하고 워커에 OCR 작업을 위임합니다.
        """
        # 1. 파일 임시 저장 (공유 볼륨)
        draft_id = str(uuid.uuid4())
        image_path = _UPLOAD_DIR / f"{draft_id}_{file.filename}"
        
        with image_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        # 2. RQ 워커에 태스크 전달
        from ai_worker.tasks.ocr_tasks import process_ocr_task
        self.queue.enqueue(
            process_ocr_task,
            args=(str(image_path), draft_id),
            job_id=f"ocr:{draft_id}"
        )

        # 3. 사용자에게는 draft_id를 즉시 반환
        return {
            "status": "processing",
            "draft_id": draft_id,
            "message": "처방전 분석을 시작했습니다. 잠시만 기다려주세요."
        }

    async def get_draft_data(self, draft_id: str) -> OcrExtractResponse | None:
        """Redis에서 워커가 완료한 데이터를 조회합니다 (Polling 대상)."""
        data_json = await self.redis.get(f"ocr_draft:{draft_id}")
        if data_json:
            return OcrExtractResponse.model_validate_json(data_json)
        return None

    async def confirm_and_save(self, request: ConfirmMedicationRequest, profile_id: str) -> dict[str, Any]:
        """최종 데이터를 DB에 저장하고, 가이드 생성 작업을 워커에 던집니다."""
        saved_meds = []

        # 1. DB 영구 저장
        for med in request.confirmed_medicines:
            daily_count = med.daily_intake_count or 1
            total_days = med.total_intake_days or 1
            total_count = daily_count * total_days

            new_med = await Medication.create(
                profile_id=profile_id,
                medicine_name=med.medicine_name,
                dose_per_intake=med.dose_per_intake,
                intake_instruction=med.intake_instruction,
                daily_intake_count=daily_count,
                total_intake_days=total_days,
                intake_times=[],
                total_intake_count=total_count,
                remaining_intake_count=total_count,
                start_date=date.today(),
                is_active=True,
            )
            saved_meds.append(new_med)

        # 2. Redis 임시 데이터 삭제
        await self.redis.delete(f"ocr_draft:{request.draft_id}")

        # 3. 가이드 생성 작업을 워커로 위임
        from ai_worker.tasks.ocr_tasks import generate_guide_task
        job_id = f"guide:{request.draft_id}"
        self.queue.enqueue(
            generate_guide_task,
            args=(json.dumps([m.model_dump() for m in request.confirmed_medicines]), profile_id, job_id),
            job_id=job_id
        )

        return {
            "status": "success",
            "message": f"{len(saved_meds)}개의 약품이 저장되었습니다. 복약 가이드를 생성 중입니다.",
            "draft_id": request.draft_id  # 가이드 조회를 위해 필요
        }

    async def get_guide_result(self, draft_id: str) -> str | None:
        """Redis에서 생성된 가이드를 조회합니다."""
        return await self.redis.get(f"guide:{draft_id}")
