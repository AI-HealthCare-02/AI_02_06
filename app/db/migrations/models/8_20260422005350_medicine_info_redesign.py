"""Integrated medicine schema for drug-data-integration + RAG Phase A.

main 브랜치의 drug-data-integration 작업과 feature/RAG의 Phase A를 병합한
단일 마이그레이션. 이 파일은 두 개의 구 마이그레이션을 대체한다:

  - (내 원본) medicine_info를 구 스키마(name/ingredient/usage/disclaimer/
    contraindicated_drugs/foods + embedding vector(768))로 생성하던 것
  - (main 원본) 8_20260422_add_rag_chunk_schema.py:
    기존 medicine_info에 ALTER로 공공 API 확장 컬럼 추가 + medicine_chunk
    + medicine_ingredient + data_sync_log 테이블 신규 생성

새 통합 스키마:
  1. medicine_info  (공공 API + RAG 메타 필드, 한 번에 CREATE)
  2. medicine_chunk (pgvector vector(768) + HNSW)
  3. medicine_ingredient (주성분 1:N)
  4. data_sync_log

멱등성 (idempotent) 보장:
  - `CREATE TABLE IF NOT EXISTS`
  - `ALTER TABLE ADD COLUMN IF NOT EXISTS`
  - `DROP COLUMN IF EXISTS`
  - 인덱스도 `IF NOT EXISTS` / `IF EXISTS`
  → 팀원 DB처럼 main #8이 이미 적용된 환경에서도 재적용 가능.

Tortoise ORM은 pgvector `vector` 타입과 HNSW 인덱스를 직접 인식하지 못하므로
embedding 컬럼과 인덱스는 raw SQL로 관리.
"""

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
        ON "data_sync_log" ("sync_type", "status");
    """


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

    DROP TABLE IF EXISTS "medicine_info";
    """
