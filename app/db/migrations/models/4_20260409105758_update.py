from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_challenges" (
    "id" UUID NOT NULL PRIMARY KEY,
    "is_active" BOOL NOT NULL DEFAULT True,
    "progress_rate" INT NOT NULL DEFAULT 0,
    "completed_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "challenge_id" UUID NOT NULL REFERENCES "challenges" ("id") ON DELETE CASCADE,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_user_challe_profile_7baf98" ON "user_challenges" ("profile_id", "challenge_id", "is_active");
COMMENT ON COLUMN "user_challenges"."is_active" IS '챌린지 참여 활성화 여부';
COMMENT ON COLUMN "user_challenges"."progress_rate" IS '진행률 (0-100)';
COMMENT ON COLUMN "user_challenges"."completed_at" IS '챌린지 최종 달성 일시';
        DROP TABLE IF EXISTS "users";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_challenges";"""


MODELS_STATE = (
    "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"
    "z/PvWkuwtQRbS7C1BGuwBH/8H0wUiXw="
)
