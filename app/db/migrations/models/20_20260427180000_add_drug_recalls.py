"""Create drug_recalls table for MFDS recall and sale-stop notices.

신규 테이블: ``drug_recalls`` (Phase 7 — 식약처 회수·판매중지 API 툴).

설계 핵심 (인계 §14.5 발견 #1, #2):

1. 🔴 복합 UNIQUE ``(item_seq, recall_command_date, recall_reason)``
   - 동일 ITEM_SEQ 가 회수 사유·일자별로 다중 row 존재 가능
     (시드 §14.5.1: `202007244` 3건, `201904809` 2건)
   - 단독 ``item_seq UNIQUE`` 면 bulk_upsert 가 두 번째 row 에서 충돌
   - 따라서 자연키는 3-tuple

2. 🔴 ``entrps_name_normalized`` 컬럼 분리
   - 원문 ``entrps_name`` 과 정규화 ``entrps_name_normalized`` 둘 다 NOT NULL
   - Q2 (제조사별 회수) 매칭 키로 정규화 컬럼 사용
   - ``동국제약(주)`` / ``(주)한독`` / ``제이더블유중외제약(주)`` 표기 정상화

3. FK 미사용 (loose join)
   - ``medicine_info.item_seq`` 와 별도 테이블 분리
   - §14.5.2 에서 회수 약 5/5 모두 ``medicine_info`` 에 ``CANCEL_NAME=정상`` 으로 존재함을 검증

인덱스: ``entrps_name_normalized`` (Q2), ``recall_command_date`` (cron diff),
``product_name`` (S7 fallback ILIKE), ``item_seq`` (Q1 매칭 다건 반환).
"""

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "drug_recalls" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "item_seq" VARCHAR(20) NOT NULL,
            "std_code" VARCHAR(32),
            "product_name" VARCHAR(200) NOT NULL,
            "entrps_name" VARCHAR(128) NOT NULL,
            "entrps_name_normalized" VARCHAR(128) NOT NULL,
            "recall_reason" TEXT NOT NULL,
            "recall_command_date" VARCHAR(8) NOT NULL,
            "sale_stop_yn" VARCHAR(1) NOT NULL DEFAULT 'N',
            "is_hospital_only" BOOLEAN NOT NULL DEFAULT FALSE,
            "is_non_drug" BOOLEAN NOT NULL DEFAULT FALSE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "uniq_drug_recall_item_seq_cmd_date_reason"
                UNIQUE ("item_seq", "recall_command_date", "recall_reason")
        );

        COMMENT ON TABLE "drug_recalls" IS
            'MFDS recall and sale-stop notices (loose join with medicine_info via item_seq)';
        COMMENT ON COLUMN "drug_recalls"."item_seq" IS
            'Drug product code (matches medicine_info.item_seq, no FK)';
        COMMENT ON COLUMN "drug_recalls"."entrps_name_normalized" IS
            'normalize_company_name(entrps_name) — Q2 matching key';
        COMMENT ON COLUMN "drug_recalls"."recall_command_date" IS
            'Recall command date YYYYMMDD — part of composite UNIQUE';
        COMMENT ON COLUMN "drug_recalls"."recall_reason" IS
            'Recall reason text — part of composite UNIQUE (allows multiple reasons per item_seq+date)';
        COMMENT ON COLUMN "drug_recalls"."is_hospital_only" IS
            'Hospital-only formulation (3차 필터: 주사·수액·이식)';
        COMMENT ON COLUMN "drug_recalls"."is_non_drug" IS
            'Non-drug product (2차 필터: 칫솔·치약·생리대 등 — RECALL_FILTER_NON_DRUG 토글)';

        CREATE INDEX IF NOT EXISTS "idx_drug_recalls_entrps_normalized"
            ON "drug_recalls" ("entrps_name_normalized");
        CREATE INDEX IF NOT EXISTS "idx_drug_recalls_command_date"
            ON "drug_recalls" ("recall_command_date" DESC);
        CREATE INDEX IF NOT EXISTS "idx_drug_recalls_product_name"
            ON "drug_recalls" ("product_name");
        CREATE INDEX IF NOT EXISTS "idx_drug_recalls_item_seq"
            ON "drug_recalls" ("item_seq");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_drug_recalls_item_seq";
        DROP INDEX IF EXISTS "idx_drug_recalls_product_name";
        DROP INDEX IF EXISTS "idx_drug_recalls_command_date";
        DROP INDEX IF EXISTS "idx_drug_recalls_entrps_normalized";
        DROP TABLE IF EXISTS "drug_recalls";
    """


# ── MODELS_STATE ────────────────────────────────────────────────────
# aerich format requirement. #19 는 raw SQL only (CREATE TABLE) 이므로
# 직전 #18 의 스냅샷을 그대로 재사용한다 (#14 와 동일 패턴). 다음
# ``aerich migrate`` 호출 시 신선한 스냅샷이 자동 생성된다.
MODELS_STATE = None
