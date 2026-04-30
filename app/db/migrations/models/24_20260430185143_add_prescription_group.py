from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "prescription_groups" (
    "id" UUID NOT NULL PRIMARY KEY,
    "department" VARCHAR(64),
    "dispensed_date" DATE,
    "source" VARCHAR(16) NOT NULL DEFAULT 'OCR',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_prescriptio_profile_123bd2" ON "prescription_groups" ("profile_id", "dispensed_date");
CREATE INDEX IF NOT EXISTS "idx_prescriptio_profile_2416cb" ON "prescription_groups" ("profile_id", "deleted_at");
COMMENT ON COLUMN "prescription_groups"."department" IS '처방 진료과 (내과/소아과 등)';
COMMENT ON COLUMN "prescription_groups"."dispensed_date" IS '처방 조제일 — 그룹 매핑 키';
COMMENT ON COLUMN "prescription_groups"."source" IS '생성 경로 (OCR/MANUAL/MIGRATED)';
COMMENT ON COLUMN "prescription_groups"."profile_id" IS '처방전 소유 프로필';
COMMENT ON TABLE "prescription_groups" IS '처방전 그룹 — medication / lifestyle_guide / challenge 의 부모 단위.';
        ALTER TABLE "medications" ADD "prescription_group_id" UUID;
        ALTER TABLE "lifestyle_guides" ADD "prescription_group_id" UUID;
        ALTER TABLE "challenges" ADD "prescription_group_id" UUID;
        COMMENT ON COLUMN "medications"."prescription_group_id" IS '소속 처방전 그룹 (한 번의 진료/처방 단위)';
COMMENT ON COLUMN "lifestyle_guides"."prescription_group_id" IS '가이드가 만들어진 처방전 그룹 (신규부터 set)';
COMMENT ON COLUMN "challenges"."prescription_group_id" IS '소속 처방전 그룹 (신규부터 set)';
        ALTER TABLE "medications" ADD CONSTRAINT "fk_medicati_prescrip_07cd88d9" FOREIGN KEY ("prescription_group_id") REFERENCES "prescription_groups" ("id") ON DELETE CASCADE;
        ALTER TABLE "lifestyle_guides" ADD CONSTRAINT "fk_lifestyl_prescrip_966ffff7" FOREIGN KEY ("prescription_group_id") REFERENCES "prescription_groups" ("id") ON DELETE CASCADE;
        ALTER TABLE "challenges" ADD CONSTRAINT "fk_challeng_prescrip_44c83d32" FOREIGN KEY ("prescription_group_id") REFERENCES "prescription_groups" ("id") ON DELETE CASCADE;

        -- ─────────────────────────────────────────────────────────────────
        -- 데이터 매핑: 기존 medication 들을 (profile_id, dispensed_date) 별로
        -- 자동 그룹핑하여 prescription_group row 생성 + medication.prescription_group_id 채움.
        -- department 는 그룹 안 medication 들의 첫 번째 값으로 박는다.
        -- 가이드 / 챌린지 의 prescription_group_id 는 NULL 유지 — 옛 데이터는
        -- "프로필 전체 활성 약물 기준" 으로 만들어진 거라 처방전 단위가 아님.
        -- 신규부터 group-bound (OCR confirm / 수동 등록 시점에 set).
        -- ─────────────────────────────────────────────────────────────────
        WITH new_groups AS (
            INSERT INTO "prescription_groups" (
                "id", "profile_id", "department", "dispensed_date",
                "source", "created_at"
            )
            SELECT
                gen_random_uuid(),
                m."profile_id",
                (array_agg(m."department") FILTER (WHERE m."department" IS NOT NULL))[1],
                m."dispensed_date",
                'MIGRATED',
                CURRENT_TIMESTAMP
            FROM "medications" m
            WHERE m."deleted_at" IS NULL
            GROUP BY m."profile_id", m."dispensed_date"
            RETURNING "id", "profile_id", "dispensed_date"
        )
        UPDATE "medications" m
        SET "prescription_group_id" = g."id"
        FROM new_groups g
        WHERE m."profile_id" = g."profile_id"
          AND m."dispensed_date" IS NOT DISTINCT FROM g."dispensed_date"
          AND m."deleted_at" IS NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lifestyle_guides" DROP CONSTRAINT IF EXISTS "fk_lifestyl_prescrip_966ffff7";
        ALTER TABLE "medications" DROP CONSTRAINT IF EXISTS "fk_medicati_prescrip_07cd88d9";
        ALTER TABLE "challenges" DROP CONSTRAINT IF EXISTS "fk_challeng_prescrip_44c83d32";
        ALTER TABLE "challenges" DROP COLUMN "prescription_group_id";
        ALTER TABLE "medications" DROP COLUMN "prescription_group_id";
        ALTER TABLE "lifestyle_guides" DROP COLUMN "prescription_group_id";
        DROP TABLE IF EXISTS "prescription_groups";"""


MODELS_STATE = (
    "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"
    "n/T8bhZg=="
)
