"""Redesign medicine_chunk: v2 수요자 중심 6-section + interaction_tags.

변경 요약 (PLAN.md §1.5.6 v2 참조):

1. section enum 재정의 (DDL 무변경 — VARCHAR(48) 컬럼 그대로)
   - v1 (13종) → v2 (6종)
   - 모델 파일의 MedicineChunkSection StrEnum 만 교체된 상태
   - medicine_chunk 테이블이 현재 0 rows 이므로 데이터 손실 없음
2. interaction_tags JSONB 컬럼 추가
   - 청크별 세분화 필터 태그 (예: ["alcohol", "condition:liver"])
   - 기본값 빈 배열
3. GIN 인덱스 (interaction_tags @> 연산자 가속)

주의사항:
- pgvector extension 은 8번 마이그레이션에서 이미 활성화됨
- medicine_chunk.embedding 컬럼은 vector(768) 타입 유지 (변경 없음)
- Tortoise 는 JSONB 타입을 TEXT 로 내보낼 수 있으므로 수동 SQL 로 jsonb 고정
"""

from tortoise import BaseDBAsyncClient


RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ── 1. interaction_tags JSONB 컬럼 추가 ───────────────────────
        -- Tortoise 의 JSONField 가 jsonb 로 내려가도록 타입 고정
        ALTER TABLE "medicine_chunk"
            ADD COLUMN IF NOT EXISTS "interaction_tags" jsonb NOT NULL DEFAULT '[]'::jsonb;

        COMMENT ON COLUMN "medicine_chunk"."interaction_tags" IS
            'JSONB array of interaction tags (see ai_worker/data/interaction_tags.json)';

        -- ── 2. GIN 인덱스 (@> 연산자 가속) ────────────────────────────
        -- 예: WHERE interaction_tags @> '["alcohol"]'
        CREATE INDEX IF NOT EXISTS "idx_medicine_chunk_tags_gin"
            ON "medicine_chunk"
            USING gin ("interaction_tags" jsonb_path_ops);

        -- ── 3. section enum 값 교체 기록 (DDL 무변경) ─────────────────
        -- VARCHAR(48) 컬럼 그대로이고 현재 medicine_chunk 가 0 rows이므로
        -- 실행할 DDL 없음. 본 섹션은 재현성 기록용 주석.
        --
        -- v1 (13종) → v2 (6종) 매핑:
        --   efficacy                     → overview
        --   usage                        → intake_guide
        --   storage                      → special_event
        --   ingredient                   → (청크 제외, medicine_ingredient 테이블 직접 조회)
        --   precaution_warning           → drug_interaction OR adverse_reaction
        --   precaution_contraindication  → drug_interaction OR special_event
        --   precaution_caution           → special_event
        --   adverse_reaction             → adverse_reaction
        --   precaution_general           → drug_interaction OR lifestyle_interaction
        --   precaution_pregnancy         → special_event (+ tag: condition:pregnancy)
        --   precaution_pediatric         → special_event (+ tag: demographic:pediatric)
        --   precaution_elderly           → special_event (+ tag: demographic:elderly)
        --   precaution_overdose          → adverse_reaction (+ tag: emergency:overdose)
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_medicine_chunk_tags_gin";
        ALTER TABLE "medicine_chunk" DROP COLUMN IF EXISTS "interaction_tags";
    """
