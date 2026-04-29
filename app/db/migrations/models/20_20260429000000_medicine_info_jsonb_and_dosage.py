"""medicine_info: precautions/side_effects TEXT -> JSONB + dosage 신규.

PLAN_DRUG_DB_INGEST.md §1 — 식약처 NB_DOC_DATA 의 카테고리별 분류를
JSONB 로 보존하기 위해 type 변경. 현재 두 컬럼 모두 NULL 상태라 데이터
손실 없음. dosage 는 UD_DOC_DATA 평문화 결과 저장용 신규 컬럼.
"""

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "medicine_info"
            ALTER COLUMN "precautions" TYPE JSONB USING NULL,
            ALTER COLUMN "side_effects" TYPE JSONB USING NULL;
        ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "dosage" TEXT;
        COMMENT ON COLUMN "medicine_info"."precautions" IS '식약처 9 카테고리(이상반응 제외) dict';
        COMMENT ON COLUMN "medicine_info"."side_effects" IS '이상반응 PARAGRAPH list';
        COMMENT ON COLUMN "medicine_info"."dosage" IS '용법용량 평문화 (UD_DOC_DATA flatten)';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "dosage";
        ALTER TABLE "medicine_info"
            ALTER COLUMN "precautions" TYPE TEXT USING NULL,
            ALTER COLUMN "side_effects" TYPE TEXT USING NULL;
    """


# MODELS_STATE: 사용자 dev 환경에서 정식 `aerich migrate` 한 번 더 실행 시 자동 갱신.
# 수동 작성한 마이그레이션이라 snapshot 비워둠 — 다음 aerich 호출이 현재 모델과
# 비교해 누락 없이 동기화한다.
