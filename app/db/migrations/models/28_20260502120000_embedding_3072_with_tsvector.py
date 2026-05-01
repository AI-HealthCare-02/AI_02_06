"""medicine_chunk: 768d → 3072d + tsvector full-text 인덱스 도입.

PLAN.md (feature/RAG) §4 Step 4 — 임베딩 모델 ko-sroberta (768d) →
OpenAI text-embedding-3-large (3072d) 마이그레이션.

본 마이그레이션의 안전성 근거:
- 현재 medicine_chunk row 0건 (baseline 측정 결과 2026-05-02 확인) →
  데이터 손실 없이 컬럼 dim 변경 가능
- HNSW 인덱스도 즉시 drop + 재생성 (재인덱싱 비용 0)
- tsvector 컬럼 + GIN 인덱스 추가 (RRF 의 BM25 score 계산 source)

DDL 변경 요약:
1. embedding 컬럼 vector(768) → vector(3072)
2. HNSW 인덱스 (cosine) drop + 재생성
3. content_tsv (tsvector) 컬럼 추가 + GIN 인덱스
4. trigger: content INSERT/UPDATE 시 content_tsv 자동 갱신 (simple config)

청킹 batch script (scripts/embed_medicine_chunks.py) 가 본 마이그레이션
직후 실행되어야 medicine_chunk 가 채워진다.
"""

from tortoise import BaseDBAsyncClient


RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ── 1. embedding 컬럼 dim 768 → 3072 ─────────────────────────
        -- 데이터 0건이라 ALTER TYPE 안전. pgvector 의 vector(N) 은 dim
        -- 변경 시 column drop+recreate 가 필요한 경우가 있어 명시 처리.
        DROP INDEX IF EXISTS "idx_medicine_chunk_embedding_hnsw";
        ALTER TABLE "medicine_chunk" DROP COLUMN IF EXISTS "embedding";
        ALTER TABLE "medicine_chunk" ADD COLUMN "embedding" vector(3072);
        COMMENT ON COLUMN "medicine_chunk"."embedding" IS
            'pgvector(3072) — OpenAI text-embedding-3-large';

        -- ── 2. HNSW 인덱스 재생성 (cosine) ───────────────────────────
        -- text-embedding-3-large 의 vector 는 L2 정규화되어 있으므로
        -- vector_cosine_ops 가 표준. ef_construction 64 / m 16 유지.
        CREATE INDEX "idx_medicine_chunk_embedding_hnsw"
            ON "medicine_chunk"
            USING hnsw ("embedding" vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

        -- ── 3. content_tsv 컬럼 추가 (RRF BM25 source) ──────────────
        -- PostgreSQL 표준 tsvector. simple config 사용 — 한국어 형태소
        -- 분석기 (mecab-ko) 는 별도 설치 필요하므로 본 PR 은 simple 만
        -- 적용. 추후 필요 시 mecab 으로 교체.
        ALTER TABLE "medicine_chunk"
            ADD COLUMN "content_tsv" tsvector;

        -- 기존 row 가 0개라 backfill 불필요. trigger 로 향후 갱신만 보장.
        CREATE OR REPLACE FUNCTION medicine_chunk_tsv_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('simple', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_medicine_chunk_tsv ON "medicine_chunk";
        CREATE TRIGGER trg_medicine_chunk_tsv
            BEFORE INSERT OR UPDATE OF content
            ON "medicine_chunk"
            FOR EACH ROW
            EXECUTE FUNCTION medicine_chunk_tsv_update();

        CREATE INDEX "idx_medicine_chunk_content_tsv_gin"
            ON "medicine_chunk"
            USING gin ("content_tsv");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_medicine_chunk_content_tsv_gin";
        DROP TRIGGER IF EXISTS trg_medicine_chunk_tsv ON "medicine_chunk";
        DROP FUNCTION IF EXISTS medicine_chunk_tsv_update();
        ALTER TABLE "medicine_chunk" DROP COLUMN IF EXISTS "content_tsv";

        DROP INDEX IF EXISTS "idx_medicine_chunk_embedding_hnsw";
        ALTER TABLE "medicine_chunk" DROP COLUMN IF EXISTS "embedding";
        ALTER TABLE "medicine_chunk" ADD COLUMN "embedding" vector(768);
        CREATE INDEX "idx_medicine_chunk_embedding_hnsw"
            ON "medicine_chunk"
            USING hnsw ("embedding" vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    """


# ── MODELS_STATE ────────────────────────────────────────────────────
# 본 마이그레이션은 raw SQL 만 변경하고 Tortoise 모델 클래스는 그대로
# (medicine_chunk.embedding 은 모델에서 fields.TextField, 실제 컬럼 타입
# 만 vector(N) 으로 raw SQL 적용). 따라서 이전 #18 의 스냅샷을 그대로
# 재사용해도 모델 정합성 유지. 다음 aerich migrate 진입 시 본 PR 의 후속
# 모델 변경 (예: medicine_chunk.content_tsv 모델 컬럼 추가) 이 있으면 그때
# 새 MODELS_STATE 갱신.
MODELS_STATE = None
