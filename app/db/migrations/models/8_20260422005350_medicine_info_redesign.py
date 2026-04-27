from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ── 0. pgvector 확장 보장 (idempotent) ───────────────────────
    CREATE EXTENSION IF NOT EXISTS vector;

    -- ── 1. medicine_info: 공공 API + RAG 메타 필드 포함 CREATE ────
    CREATE TABLE IF NOT EXISTS "medicine_info" (
        "id" SERIAL NOT NULL PRIMARY KEY,
        "item_seq" VARCHAR(20) UNIQUE,
        "medicine_name" VARCHAR(200) NOT NULL UNIQUE,
        "item_eng_name" VARCHAR(256),
        "entp_name" VARCHAR(128),
        "product_type" VARCHAR(64),
        "spclty_pblc" VARCHAR(32),
        "permit_date" VARCHAR(8),
        "cancel_name" VARCHAR(16),
        "main_item_ingr" TEXT,
        "storage_method" TEXT,
        "edi_code" VARCHAR(256),
        "bizrno" VARCHAR(16),
        "change_date" VARCHAR(8),
        "category" VARCHAR(64),
        "efficacy" TEXT,
        "side_effects" TEXT,
        "precautions" TEXT,
        "chart" TEXT,
        "material_name" TEXT,
        "valid_term" VARCHAR(64),
        "pack_unit" VARCHAR(256),
        "atc_code" VARCHAR(32),
        "ee_doc_url" VARCHAR(256),
        "ud_doc_url" VARCHAR(256),
        "nb_doc_url" VARCHAR(256),
        "last_synced_at" TIMESTAMPTZ,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- 팀원 main #8이 이미 적용된 DB 대응: 누락 컬럼만 idempotent 추가
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "chart" TEXT;
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "material_name" TEXT;
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "valid_term" VARCHAR(64);
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "pack_unit" VARCHAR(256);
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "atc_code" VARCHAR(32);
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "ee_doc_url" VARCHAR(256);
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "ud_doc_url" VARCHAR(256);
    ALTER TABLE "medicine_info" ADD COLUMN IF NOT EXISTS "nb_doc_url" VARCHAR(256);
    ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "embedding";

    COMMENT ON COLUMN "medicine_info"."item_seq" IS '품목기준코드 (ITEM_SEQ, UPSERT key)';
    COMMENT ON COLUMN "medicine_info"."medicine_name" IS '약품명 (ITEM_NAME)';
    COMMENT ON COLUMN "medicine_info"."item_eng_name" IS '영문 약품명 (ITEM_ENG_NAME)';
    COMMENT ON COLUMN "medicine_info"."entp_name" IS '제조업체명 (ENTP_NAME)';
    COMMENT ON COLUMN "medicine_info"."product_type" IS '제품 유형 (PRDUCT_TYPE)';
    COMMENT ON COLUMN "medicine_info"."spclty_pblc" IS '전문/일반의약품 구분 (SPCLTY_PBLC)';
    COMMENT ON COLUMN "medicine_info"."permit_date" IS '허가일자 YYYYMMDD (ITEM_PERMIT_DATE)';
    COMMENT ON COLUMN "medicine_info"."cancel_name" IS '상태 정상/취소 (CANCEL_NAME)';
    COMMENT ON COLUMN "medicine_info"."main_item_ingr" IS '유효성분 (MAIN_ITEM_INGR)';
    COMMENT ON COLUMN "medicine_info"."storage_method" IS '저장방법 (STORAGE_METHOD)';
    COMMENT ON COLUMN "medicine_info"."edi_code" IS '보험코드 (EDI_CODE)';
    COMMENT ON COLUMN "medicine_info"."bizrno" IS '사업자등록번호 (BIZRNO)';
    COMMENT ON COLUMN "medicine_info"."change_date" IS '변경일자 YYYYMMDD';
    COMMENT ON COLUMN "medicine_info"."category" IS '약품 분류 (검색 필터용)';
    COMMENT ON COLUMN "medicine_info"."efficacy" IS '효능/효과';
    COMMENT ON COLUMN "medicine_info"."side_effects" IS '부작용';
    COMMENT ON COLUMN "medicine_info"."precautions" IS '주의사항';
    COMMENT ON COLUMN "medicine_info"."chart" IS '성상 (CHART)';
    COMMENT ON COLUMN "medicine_info"."material_name" IS '총량/분량 원본 문자열 (MATERIAL_NAME)';
    COMMENT ON COLUMN "medicine_info"."valid_term" IS '유효기간 (VALID_TERM)';
    COMMENT ON COLUMN "medicine_info"."pack_unit" IS '포장단위 (PACK_UNIT)';
    COMMENT ON COLUMN "medicine_info"."atc_code" IS 'WHO ATC 분류코드 (ATC_CODE)';
    COMMENT ON COLUMN "medicine_info"."ee_doc_url" IS '효능 PDF URL (EE_DOC_ID)';
    COMMENT ON COLUMN "medicine_info"."ud_doc_url" IS '용법 PDF URL (UD_DOC_ID)';
    COMMENT ON COLUMN "medicine_info"."nb_doc_url" IS '주의사항 PDF URL (NB_DOC_ID)';
    COMMENT ON COLUMN "medicine_info"."last_synced_at" IS '마지막 공공 API 동기화 시각';
    COMMENT ON TABLE "medicine_info" IS 'Pharmaceutical knowledge base for RAG search and public API data';

    -- ── 2. medicine_chunk: 섹션별 임베딩 청크 (vector(768) + HNSW) ──
    CREATE TABLE IF NOT EXISTS "medicine_chunk" (
        "id" BIGSERIAL NOT NULL PRIMARY KEY,
        "medicine_info_id" INT NOT NULL
            REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
        "section" VARCHAR(48) NOT NULL,
        "chunk_index" INT NOT NULL DEFAULT 0,
        "content" TEXT NOT NULL,
        "token_count" INT,
        "embedding" vector(768),
        "model_version" VARCHAR(64) NOT NULL,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT "uq_medicine_chunk_section"
            UNIQUE ("medicine_info_id", "section", "chunk_index")
    );

    COMMENT ON TABLE "medicine_chunk" IS
        'Section-level embedding chunks for RAG similarity search';
    COMMENT ON COLUMN "medicine_chunk"."section" IS
        'Chunk section tag (MedicineChunkSection enum, 13 values)';
    COMMENT ON COLUMN "medicine_chunk"."chunk_index" IS
        'Sub-chunk order when section ARTICLE exceeds token limit';
    COMMENT ON COLUMN "medicine_chunk"."content" IS
        'Final embedding-target text with header prefix';
    COMMENT ON COLUMN "medicine_chunk"."token_count" IS 'Token count for monitoring';
    COMMENT ON COLUMN "medicine_chunk"."embedding" IS 'pgvector(768) dense embedding';
    COMMENT ON COLUMN "medicine_chunk"."model_version" IS
        'Embedding model identifier (e.g. ko-sroberta-multitask-v1)';

    CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_medicine_info_id"
        ON "medicine_chunk" ("medicine_info_id");
    CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_section"
        ON "medicine_chunk" ("section");
    CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_model_version"
        ON "medicine_chunk" ("model_version");
    CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_embedding_hnsw"
        ON "medicine_chunk" USING hnsw ("embedding" vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

    -- ── 3. medicine_ingredient: 주성분 1:N ───────────────────────
    CREATE TABLE IF NOT EXISTS "medicine_ingredient" (
        "id" BIGSERIAL NOT NULL PRIMARY KEY,
        "medicine_info_id" INT NOT NULL
            REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
        "mtral_sn" INT NOT NULL,
        "mtral_code" VARCHAR(16),
        "mtral_name" VARCHAR(128) NOT NULL,
        "main_ingr_eng" VARCHAR(256),
        "quantity" VARCHAR(32),
        "unit" VARCHAR(16),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT "uq_medicine_ingredient_sn"
            UNIQUE ("medicine_info_id", "mtral_sn")
    );

    COMMENT ON TABLE "medicine_ingredient" IS
        'Drug active ingredients (1:N from medicine_info)';
    COMMENT ON COLUMN "medicine_ingredient"."mtral_sn" IS
        'Ingredient sequence number within the drug (API MTRAL_SN)';
    COMMENT ON COLUMN "medicine_ingredient"."mtral_code" IS
        'Ingredient standard code (API MTRAL_CODE)';
    COMMENT ON COLUMN "medicine_ingredient"."mtral_name" IS
        'Korean ingredient name (API MTRAL_NM)';
    COMMENT ON COLUMN "medicine_ingredient"."main_ingr_eng" IS
        'English ingredient name (API MAIN_INGR_ENG)';
    COMMENT ON COLUMN "medicine_ingredient"."quantity" IS
        'Ingredient quantity (API QNT)';
    COMMENT ON COLUMN "medicine_ingredient"."unit" IS
        'Quantity unit (API INGD_UNIT_CD)';

    CREATE INDEX IF NOT EXISTS "idx_medicine_ingredient_mtral_name"
        ON "medicine_ingredient" ("mtral_name");
    CREATE INDEX IF NOT EXISTS "idx_medicine_ingredient_mtral_code"
        ON "medicine_ingredient" ("mtral_code");

    -- ── 4. data_sync_log: 동기화 이력 ────────────────────────────
    CREATE TABLE IF NOT EXISTS "data_sync_log" (
        "id" BIGSERIAL NOT NULL PRIMARY KEY,
        "sync_type" VARCHAR(32) NOT NULL,
        "sync_date" TIMESTAMPTZ NOT NULL,
        "total_fetched" INT NOT NULL DEFAULT 0,
        "total_inserted" INT NOT NULL DEFAULT 0,
        "total_updated" INT NOT NULL DEFAULT 0,
        "status" VARCHAR(16) NOT NULL,
        "error_message" TEXT,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    COMMENT ON TABLE "data_sync_log" IS 'Public API data synchronization history';
    COMMENT ON COLUMN "data_sync_log"."sync_type" IS 'Sync target type (e.g. medicine_info)';
    COMMENT ON COLUMN "data_sync_log"."sync_date" IS 'Sync execution timestamp';
    COMMENT ON COLUMN "data_sync_log"."total_fetched" IS 'Total records fetched from API';
    COMMENT ON COLUMN "data_sync_log"."total_inserted" IS 'Number of newly inserted records';
    COMMENT ON COLUMN "data_sync_log"."total_updated" IS 'Number of updated existing records';
    COMMENT ON COLUMN "data_sync_log"."status" IS 'Sync result status (SUCCESS / FAILED)';
    COMMENT ON COLUMN "data_sync_log"."error_message" IS 'Error details when sync fails';

    CREATE INDEX IF NOT EXISTS "idx_data_sync_log_type_status"
        ON "data_sync_log" ("sync_type", "status");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_data_sync_log_type_status";
    DROP TABLE IF EXISTS "data_sync_log";

    DROP INDEX IF EXISTS "idx_medicine_ingredient_mtral_code";
    DROP INDEX IF EXISTS "idx_medicine_ingredient_mtral_name";
    DROP TABLE IF EXISTS "medicine_ingredient";

    DROP INDEX IF EXISTS "idx_medicine_chunk_embedding_hnsw";
    DROP INDEX IF EXISTS "idx_medicine_chunk_model_version";
    DROP INDEX IF EXISTS "idx_medicine_chunk_section";
    DROP INDEX IF EXISTS "idx_medicine_chunk_medicine_info_id";
    DROP TABLE IF EXISTS "medicine_chunk";

    DROP TABLE IF EXISTS "medicine_info";"""


MODELS_STATE = (
    "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"
    "2G2j77bRt9Sw+pm30RdTpFa7j/7XfwFKI2Eb"
)
