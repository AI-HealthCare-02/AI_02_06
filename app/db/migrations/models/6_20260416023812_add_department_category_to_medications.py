from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_intake_logs_profile_2b24b8";
        DROP INDEX IF EXISTS "idx_medications_medicin_e9835c";
        ALTER TABLE "profiles" ALTER COLUMN "health_survey" TYPE JSONB USING "health_survey"::JSONB;
        ALTER TABLE "medications" ADD "daily_intake_count" INT;
        ALTER TABLE "medications" ADD "department" VARCHAR(64);
        ALTER TABLE "medications" ADD "category" VARCHAR(64);
        ALTER TABLE "medications" ADD "total_intake_days" INT;
        ALTER TABLE "medications" ALTER COLUMN "intake_times" TYPE JSONB USING "intake_times"::JSONB;
        ALTER TABLE "challenges" ALTER COLUMN "completed_dates" TYPE JSONB USING "completed_dates"::JSONB;
        ALTER TABLE "message_feedbacks" ALTER COLUMN "metadata" TYPE JSONB USING "metadata"::JSONB;
        ALTER TABLE "drug_interaction_cache" ALTER COLUMN "interaction" TYPE JSONB USING "interaction"::JSONB;
        ALTER TABLE "llm_response_cache" ALTER COLUMN "response" TYPE JSONB USING "response"::JSONB;
        COMMENT ON COLUMN "medications"."daily_intake_count" IS '1일 복용 횟수';
COMMENT ON COLUMN "medications"."department" IS '처방 진료과 (예: 내과)';
COMMENT ON COLUMN "medications"."category" IS '약품 분류 (예: 해열진통제)';
COMMENT ON COLUMN "medications"."total_intake_days" IS '총 복용 일수';
        DROP TABLE IF EXISTS "user_challenges";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "profiles" ALTER COLUMN "health_survey" TYPE JSONB USING "health_survey"::JSONB;
        ALTER TABLE "challenges" ALTER COLUMN "completed_dates" TYPE JSONB USING "completed_dates"::JSONB;
        ALTER TABLE "medications" DROP COLUMN "daily_intake_count";
        ALTER TABLE "medications" DROP COLUMN "department";
        ALTER TABLE "medications" DROP COLUMN "category";
        ALTER TABLE "medications" DROP COLUMN "total_intake_days";
        ALTER TABLE "medications" ALTER COLUMN "intake_times" TYPE JSONB USING "intake_times"::JSONB;
        ALTER TABLE "message_feedbacks" ALTER COLUMN "metadata" TYPE JSONB USING "metadata"::JSONB;
        ALTER TABLE "llm_response_cache" ALTER COLUMN "response" TYPE JSONB USING "response"::JSONB;
        ALTER TABLE "drug_interaction_cache" ALTER COLUMN "interaction" TYPE JSONB USING "interaction"::JSONB;
        CREATE INDEX IF NOT EXISTS "idx_intake_logs_profile_2b24b8" ON "intake_logs" ("profile_id", "medication_id", "created_at");
        CREATE INDEX IF NOT EXISTS "idx_medications_medicin_e9835c" ON "medications" ("medicine_name");"""


MODELS_STATE = (
    "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"
    "qDrT7Y6oM16IM//w9CmnGV"
)
