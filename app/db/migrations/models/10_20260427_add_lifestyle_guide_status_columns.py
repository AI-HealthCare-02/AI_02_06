from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lifestyle_guides"
            ADD COLUMN IF NOT EXISTS "status" VARCHAR(16) NOT NULL DEFAULT 'ready',
            ADD COLUMN IF NOT EXISTS "processed_at" TIMESTAMPTZ NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lifestyle_guides"
            DROP COLUMN IF EXISTS "status",
            DROP COLUMN IF EXISTS "processed_at";
    """
