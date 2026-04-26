"""Create ocr_drafts table for DB-only OCR draft persistence.

기존: OCR 결과를 Redis (ocr_draft:{id} / ocr_status:{id}) 에 임시 저장 -> 사용자가
페이지를 닫으면 draft_id 를 잃어버려 결과 회수 불가.

신규: ``ocr_drafts`` 테이블에 영구 저장 (24h 정책). 사용자가 main 페이지로 돌아오면
``profile_id`` 기준으로 active draft 조회 -> 처리중·확인대기 상태 표시 가능.

Dedup: 같은 사용자 + 같은 image_hash + consumed_at IS NULL 이면 기존 draft 재사용.

본 마이그레이션은 raw SQL only — Tortoise 모델은 별도 PR 에서 등록되며 본 #14 의
MODELS_STATE 는 직전 #13 의 스냅샷을 그대로 사용한다 (모델 자체 추가는 아래
INSERT/CREATE 에 일치하지 않을 수 있으나 다음 modeling 작업에서 동기화).
"""

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ocr_drafts" (
            "id" UUID NOT NULL PRIMARY KEY,
            "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE,
            "status" VARCHAR(16) NOT NULL DEFAULT 'pending',
            "medicines" JSONB NOT NULL DEFAULT '[]'::jsonb,
            "filename" VARCHAR(256),
            "image_hash" VARCHAR(64) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "processed_at" TIMESTAMPTZ,
            "consumed_at" TIMESTAMPTZ
        );

        COMMENT ON TABLE "ocr_drafts" IS '처방전 OCR 처리 결과 임시 저장 (24h 정책, profile 별 회수 가능)';
        COMMENT ON COLUMN "ocr_drafts"."status" IS 'pending / ready / no_text / no_candidates / failed';
        COMMENT ON COLUMN "ocr_drafts"."medicines" IS 'ai-worker 가 채우는 ExtractedMedicine 리스트 직렬화';
        COMMENT ON COLUMN "ocr_drafts"."image_hash" IS 'SHA256(image_bytes) — 동일 사용자 dedup 키';
        COMMENT ON COLUMN "ocr_drafts"."consumed_at" IS 'confirm 으로 DB 영구 저장 완료 시점';

        CREATE INDEX IF NOT EXISTS "idx_ocr_drafts_profile_active"
            ON "ocr_drafts" ("profile_id", "created_at" DESC)
            WHERE "consumed_at" IS NULL;
        CREATE INDEX IF NOT EXISTS "idx_ocr_drafts_dedup"
            ON "ocr_drafts" ("profile_id", "image_hash")
            WHERE "consumed_at" IS NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_ocr_drafts_dedup";
        DROP INDEX IF EXISTS "idx_ocr_drafts_profile_active";
        DROP TABLE IF EXISTS "ocr_drafts";
    """


# ── MODELS_STATE ────────────────────────────────────────────────────
# aerich format requirement. #14 는 raw SQL only (CREATE TABLE) 이지만
# 신규 모델을 추가하므로 다음 ``aerich migrate`` 호출 시 신선한 스냅샷이
# 자동 생성된다. 본 #14 는 호환을 위해 직전 #13 의 스냅샷을 일단 재사용.
MODELS_STATE = (
    "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"
)
