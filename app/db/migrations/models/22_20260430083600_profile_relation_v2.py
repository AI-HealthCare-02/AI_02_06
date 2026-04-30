from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 1) gender 컬럼 추가 (NULL 허용 — 데이터 마이그레이션이 채움)
        ALTER TABLE "profiles" ADD "gender" VARCHAR(8);
        COMMENT ON COLUMN "profiles"."gender" IS 'MALE: MALE\\nFEMALE: FEMALE';

        -- 2) RelationType enum 8종 갱신 (PostgreSQL CharEnumField 는 COMMENT 기반)
        COMMENT ON COLUMN "profiles"."relation_type" IS 'SELF: SELF
FATHER: FATHER
MOTHER: MOTHER
SON: SON
DAUGHTER: DAUGHTER
HUSBAND: HUSBAND
WIFE: WIFE
OTHER: OTHER';

        -- 3) 데이터 마이그레이션 — SELF 의 gender 추출 (health_survey JSON)
        UPDATE "profiles"
        SET "gender" = CAST(health_survey ->> 'gender' AS VARCHAR(8))
        WHERE relation_type = 'SELF'
          AND health_survey ->> 'gender' IN ('MALE', 'FEMALE');

        -- 4) 가족 row: PARENT/CHILD/SPOUSE × gender(JSON) 조합 → 새 enum 8종
        UPDATE "profiles" SET "relation_type" = 'FATHER',   "gender" = 'MALE'
            WHERE relation_type = 'PARENT' AND health_survey ->> 'gender' = 'MALE';
        UPDATE "profiles" SET "relation_type" = 'MOTHER',   "gender" = 'FEMALE'
            WHERE relation_type = 'PARENT' AND health_survey ->> 'gender' = 'FEMALE';
        UPDATE "profiles" SET "relation_type" = 'SON',      "gender" = 'MALE'
            WHERE relation_type = 'CHILD'  AND health_survey ->> 'gender' = 'MALE';
        UPDATE "profiles" SET "relation_type" = 'DAUGHTER', "gender" = 'FEMALE'
            WHERE relation_type = 'CHILD'  AND health_survey ->> 'gender' = 'FEMALE';
        UPDATE "profiles" SET "relation_type" = 'HUSBAND',  "gender" = 'MALE'
            WHERE relation_type = 'SPOUSE' AND health_survey ->> 'gender' = 'MALE';
        UPDATE "profiles" SET "relation_type" = 'WIFE',     "gender" = 'FEMALE'
            WHERE relation_type = 'SPOUSE' AND health_survey ->> 'gender' = 'FEMALE';

        -- 5) 매핑 안 된 잔여 PARENT/CHILD/SPOUSE → OTHER 강등 (gender 정보 없는 row)
        UPDATE "profiles" SET "relation_type" = 'OTHER'
            WHERE relation_type IN ('PARENT', 'CHILD', 'SPOUSE');"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 새 enum row 들을 옛 enum 으로 best-effort 되돌림
        UPDATE "profiles" SET relation_type = 'PARENT' WHERE relation_type IN ('FATHER', 'MOTHER');
        UPDATE "profiles" SET relation_type = 'CHILD'  WHERE relation_type IN ('SON', 'DAUGHTER');
        UPDATE "profiles" SET relation_type = 'SPOUSE' WHERE relation_type IN ('HUSBAND', 'WIFE');

        ALTER TABLE "profiles" DROP COLUMN "gender";
        COMMENT ON COLUMN "profiles"."relation_type" IS 'SELF: SELF
PARENT: PARENT
CHILD: CHILD
SPOUSE: SPOUSE
OTHER: OTHER';"""


MODELS_STATE = (
    "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"
    "ZILLKxKx//+f9ZM/oe"
)
