import json
from pathlib import Path

from openai import OpenAI
from tortoise import Tortoise

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)


async def run_initial_embedding_task(json_path: str = "ai_worker/data/medicines.json") -> bool:
    """[RQ Task] 초기 약학 지식 베이스 임베딩 및 DB 적재."""
    logger.info(f"Starting initial embedding task from {json_path}")

    # 1. JSON 데이터 로드
    path = Path(json_path)
    if not path.exists():
        logger.error(f"File not found: {json_path}")
        return False

    with path.open(encoding="utf-8") as f:
        medicines = json.load(f)

    # 2. OpenAI 클라이언트 및 DB 연결
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    conn = Tortoise.get_connection("default")

    # 3. pgvector 확장 활성화 (사전 작업)
    await conn.execute_script("CREATE EXTENSION IF NOT EXISTS vector;")
    # Tortoise 모델이 생성되었어도 vector 타입은 수동 조정이 필요할 수 있으므로 강제 적용
    await conn.execute_script(
        "ALTER TABLE medicine_info ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector;"
    )

    success_count = 0
    for med in medicines:
        try:
            name = med.get("medicine_name")
            # 임베딩할 텍스트 생성 (이름 + 효능 + 주의사항 결합)
            input_text = (
                f"약품명: {name}\n"
                f"효능: {med.get('efficacy', '')}\n"
                f"부작용: {med.get('side_effects', '')}\n"
                f"주의사항: {med.get('precautions', '')}"
            )

            # OpenAI 임베딩 호출
            response = client.embeddings.create(input=input_text, model="text-embedding-3-small")
            embedding_vector = response.data[0].embedding

            # Raw SQL로 저장 (UPSERT)
            sql = """
                INSERT INTO medicine_info
                    (medicine_name, category, efficacy, side_effects,
                     precautions, embedding, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6::vector, NOW(), NOW())
                ON CONFLICT (medicine_name) DO UPDATE SET
                    category = EXCLUDED.category,
                    efficacy = EXCLUDED.efficacy,
                    side_effects = EXCLUDED.side_effects,
                    precautions = EXCLUDED.precautions,
                    embedding = EXCLUDED.embedding,
                    updated_at = NOW();
            """
            await conn.execute_query(
                sql,
                [
                    name,
                    med.get("category"),
                    med.get("efficacy"),
                    med.get("side_effects"),
                    med.get("precautions"),
                    str(embedding_vector),
                ],
            )
            success_count += 1
            if success_count % 10 == 0:
                logger.info(f"Progress: {success_count}/{len(medicines)} medicines embedded.")

        except Exception as e:
            logger.error(f"Error embedding {med.get('medicine_name')}: {e}")

    logger.info(f"Embedding task completed. Total {success_count} medicines added/updated.")
    return True
