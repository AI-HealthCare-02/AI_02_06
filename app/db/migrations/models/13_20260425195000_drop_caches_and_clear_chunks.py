"""Drop unused cache tables + clear medicine_chunk for 6-section re-embedding.

본 마이그레이션은 origin/main 통합 작업의 최종 수렴 단계 (Step 4).

변경 사항:
- ``drug_interaction_cache`` 테이블 DROP — 서비스 코드에서 미사용 확인됨
- ``llm_response_cache`` 테이블 DROP — medication_service 의 캐싱 로직과 함께 제거
- ``mock_items`` 테이블 DROP IF EXISTS — 코드·마이그레이션 어디에도 정의 없음,
  과거 잔재 가능성 있어 안전 정리
- ``medicine_chunk`` 데이터 DELETE — section enum 이 13종(v1) → 6종(v2,
  사용자 질문 패턴 기반) 으로 교체되어 의미적 매핑 불가. 재임베딩 필요.
  (테스트 데이터 한정이라 손실 허용 정책 적용)

다운그레이드:
- 캐시 두 테이블의 원본 CREATE 문 복원 (#0 init 에서 가져옴)
- mock_items 는 원래 정의가 없어 복원 대상 아님
- medicine_chunk 데이터는 복원 불가 (재임베딩 필요)
"""

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 1. medicine_chunk 데이터 정리 (13섹션 -> 6섹션 재임베딩 전제)
        DELETE FROM "medicine_chunk";

        -- 2. 사용하지 않는 캐시 테이블 제거
        DROP TABLE IF EXISTS "drug_interaction_cache";
        DROP TABLE IF EXISTS "llm_response_cache";

        -- 3. 정의 없는 잔재 테이블 안전 정리
        DROP TABLE IF EXISTS "mock_items";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- llm_response_cache 복원 (#0 init 의 원본 정의)
        CREATE TABLE IF NOT EXISTS "llm_response_cache" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "prompt_hash" VARCHAR(64) NOT NULL UNIQUE,
            "prompt_text" TEXT NOT NULL,
            "response" JSONB NOT NULL,
            "hit_count" INT NOT NULL DEFAULT 0,
            "expires_at" TIMESTAMPTZ NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_llm_respons_prompt__2d135a"
            ON "llm_response_cache" ("prompt_hash");
        CREATE INDEX IF NOT EXISTS "idx_llm_respons_expires_418e4a"
            ON "llm_response_cache" ("expires_at");

        -- drug_interaction_cache 복원 (#0 init 의 원본 정의)
        CREATE TABLE IF NOT EXISTS "drug_interaction_cache" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "drug_pair" VARCHAR(256) NOT NULL UNIQUE,
            "interaction" JSONB NOT NULL,
            "expires_at" TIMESTAMPTZ NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_drug_intera_drug_pa_abfbd4"
            ON "drug_interaction_cache" ("drug_pair");
        CREATE INDEX IF NOT EXISTS "idx_drug_intera_expires_b14542"
            ON "drug_interaction_cache" ("expires_at");

        -- medicine_chunk 데이터: 복원 불가 (재임베딩 필요)
        -- mock_items: 원본 정의 없음 (복원 대상 아님)
    """
