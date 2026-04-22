"""Add RAG chunk schema: medicine_chunk + medicine_ingredient + medicine_info extension.

변경 요약 (PLAN.md §1.5 참조):

1. medicine_info
   - DROP 컬럼: embedding (청크 테이블로 이관)
   - ADD 컬럼: chart, material_name, valid_term, pack_unit, atc_code,
              ee_doc_url, ud_doc_url, nb_doc_url

2. medicine_chunk (신규)
   - 섹션별 임베딩 청크 테이블
   - embedding 컬럼은 pgvector VECTOR(768) 타입 (수동 SQL 적용)
   - HNSW 인덱스 (vector_cosine_ops, m=16, ef_construction=64)

3. medicine_ingredient (신규)
   - 주성분 1:N 상세 테이블 (공공데이터 주성분 상세 API)

주의사항:
- pgvector extension이 PostgreSQL 인스턴스에 사전 설치되어 있어야 함
  (담당자가 사전 확인 완료)
- medicine_info.embedding 기존 값은 담당자가 사전 백업/검증 후 DROP
- 본 파일은 Aerich 자동 생성 + pgvector 수동 SQL 병합본
  (MODELS_STATE는 `aerich migrate --name empty_sync` 후 재생성 필요 시 보강)
"""

from tortoise import BaseDBAsyncClient


RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ── 0. pgvector 확장 보장 (idempotent) ───────────────────────
        CREATE EXTENSION IF NOT EXISTS vector;

        -- ── 1. medicine_info 기존 embedding 컬럼 제거 ────────────────
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "embedding";

        -- ── 2. medicine_info 신규 컬럼 8종 추가 ──────────────────────
        ALTER TABLE "medicine_info" ADD COLUMN "chart" TEXT;
        ALTER TABLE "medicine_info" ADD COLUMN "material_name" TEXT;
        ALTER TABLE "medicine_info" ADD COLUMN "valid_term" VARCHAR(64);
        ALTER TABLE "medicine_info" ADD COLUMN "pack_unit" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD COLUMN "atc_code" VARCHAR(32);
        ALTER TABLE "medicine_info" ADD COLUMN "ee_doc_url" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD COLUMN "ud_doc_url" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD COLUMN "nb_doc_url" VARCHAR(256);

        COMMENT ON COLUMN "medicine_info"."chart" IS '성상 (CHART)';
        COMMENT ON COLUMN "medicine_info"."material_name" IS '총량/분량 원본 문자열 (MATERIAL_NAME)';
        COMMENT ON COLUMN "medicine_info"."valid_term" IS '유효기간 (VALID_TERM)';
        COMMENT ON COLUMN "medicine_info"."pack_unit" IS '포장단위 (PACK_UNIT)';
        COMMENT ON COLUMN "medicine_info"."atc_code" IS 'WHO ATC 분류코드 (ATC_CODE)';
        COMMENT ON COLUMN "medicine_info"."ee_doc_url" IS '효능 PDF URL (EE_DOC_ID)';
        COMMENT ON COLUMN "medicine_info"."ud_doc_url" IS '용법 PDF URL (UD_DOC_ID)';
        COMMENT ON COLUMN "medicine_info"."nb_doc_url" IS '주의사항 PDF URL (NB_DOC_ID)';

        -- ── 3. medicine_chunk 테이블 생성 (embedding은 임시 TEXT) ────
        CREATE TABLE IF NOT EXISTS "medicine_chunk" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "medicine_info_id" INT NOT NULL
                REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
            "section" VARCHAR(48) NOT NULL,
            "chunk_index" INT NOT NULL DEFAULT 0,
            "content" TEXT NOT NULL,
            "token_count" INT,
            "embedding" TEXT,
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
            'Sub-chunk order when ARTICLE exceeds token limit';
        COMMENT ON COLUMN "medicine_chunk"."model_version" IS
            'Embedding model version (e.g. ko-sroberta-multitask-v1)';

        CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_parent"
            ON "medicine_chunk" ("medicine_info_id");
        CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_section"
            ON "medicine_chunk" ("section");
        CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_model_version"
            ON "medicine_chunk" ("model_version");

        -- ── 4. medicine_chunk.embedding 컬럼을 vector(768)로 치환 ───
        -- Tortoise ORM은 pgvector 타입을 모르므로 TEXT → vector(768) 변환.
        -- 초기 생성 직후 데이터가 없으므로 USING 절 불필요.
        ALTER TABLE "medicine_chunk" DROP COLUMN "embedding";
        ALTER TABLE "medicine_chunk" ADD COLUMN "embedding" vector(768);

        -- ── 5. HNSW 인덱스 (pgvector 0.5+) ───────────────────────────
        -- m=16, ef_construction=64: 20만 벡터 규모 권장값
        CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_embedding_hnsw"
            ON "medicine_chunk"
            USING hnsw ("embedding" vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

        -- ── 6. medicine_ingredient 테이블 생성 ───────────────────────
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

        CREATE INDEX IF NOT EXISTS "idx_medicine_ingredient_name"
            ON "medicine_ingredient" ("mtral_name");
        CREATE INDEX IF NOT EXISTS "idx_medicine_ingredient_code"
            ON "medicine_ingredient" ("mtral_code");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ── 역순 롤백 ─────────────────────────────────────────────────
        DROP INDEX IF EXISTS "idx_medicine_ingredient_code";
        DROP INDEX IF EXISTS "idx_medicine_ingredient_name";
        DROP TABLE IF EXISTS "medicine_ingredient";

        DROP INDEX IF EXISTS "idx_medicine_chunk_embedding_hnsw";
        DROP INDEX IF EXISTS "idx_medicine_chunk_model_version";
        DROP INDEX IF EXISTS "idx_medicine_chunk_section";
        DROP INDEX IF EXISTS "idx_medicine_chunk_parent";
        DROP TABLE IF EXISTS "medicine_chunk";

        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "nb_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "ud_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "ee_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "atc_code";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "pack_unit";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "valid_term";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "material_name";
        ALTER TABLE "medicine_info" DROP COLUMN IF EXISTS "chart";

        ALTER TABLE "medicine_info" ADD COLUMN "embedding" TEXT;
    """
