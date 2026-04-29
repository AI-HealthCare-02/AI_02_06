from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "medicine_ingredient" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "mtral_sn" INT NOT NULL,
    "mtral_code" VARCHAR(16),
    "mtral_name" VARCHAR(128) NOT NULL,
    "main_ingr_eng" VARCHAR(256),
    "quantity" VARCHAR(32),
    "unit" VARCHAR(16),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "medicine_info_id" INT NOT NULL REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_medicine_in_medicin_8f85f4" UNIQUE ("medicine_info_id", "mtral_sn")
);
CREATE INDEX IF NOT EXISTS "idx_medicine_in_mtral_n_3e3034" ON "medicine_ingredient" ("mtral_name");
CREATE INDEX IF NOT EXISTS "idx_medicine_in_mtral_c_705f45" ON "medicine_ingredient" ("mtral_code");
COMMENT ON COLUMN "medicine_ingredient"."mtral_sn" IS 'Ingredient sequence number within the drug (API MTRAL_SN)';
COMMENT ON COLUMN "medicine_ingredient"."mtral_code" IS 'Ingredient standard code (API MTRAL_CODE)';
COMMENT ON COLUMN "medicine_ingredient"."mtral_name" IS 'Korean ingredient name (API MTRAL_NM)';
COMMENT ON COLUMN "medicine_ingredient"."main_ingr_eng" IS 'English ingredient name (API MAIN_INGR_ENG)';
COMMENT ON COLUMN "medicine_ingredient"."quantity" IS 'Ingredient quantity (API QNT)';
COMMENT ON COLUMN "medicine_ingredient"."unit" IS 'Quantity unit (API INGD_UNIT_CD)';
COMMENT ON COLUMN "medicine_ingredient"."medicine_info_id" IS 'Parent medicine_info reference';
COMMENT ON TABLE "medicine_ingredient" IS 'Drug active ingredients (1:N from medicine_info)';
        ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "dosage" TEXT;
        ALTER TABLE "medicine_info" ALTER COLUMN "side_effects" TYPE JSONB USING NULL;
        ALTER TABLE "medicine_info" ALTER COLUMN "precautions" TYPE JSONB USING NULL;
        COMMENT ON COLUMN "medicine_info"."side_effects" IS '이상반응 PARAGRAPH list (NB_DOC_DATA 4번 이상반응 카테고리)';
        COMMENT ON COLUMN "medicine_info"."precautions" IS '식약처 9 카테고리(이상반응 제외) dict (key: 경고/금기/신중 투여/일반적 주의/임부/소아/고령자/과량/적용상)';
        COMMENT ON COLUMN "medicine_info"."dosage" IS '용법용량 평문화 (UD_DOC_DATA flatten plaintext)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "dosage";
        ALTER TABLE "medicine_info" ALTER COLUMN "side_effects" TYPE TEXT USING NULL;
        ALTER TABLE "medicine_info" ALTER COLUMN "precautions" TYPE TEXT USING NULL;
        DROP TABLE IF EXISTS "medicine_ingredient";"""


MODELS_STATE = ""
