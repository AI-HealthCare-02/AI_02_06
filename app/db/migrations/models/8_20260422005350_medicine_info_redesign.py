from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS "medicine_info" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(128) NOT NULL UNIQUE,
    "ingredient" TEXT NOT NULL,
    "usage" VARCHAR(64) NOT NULL,
    "disclaimer" TEXT NOT NULL,
    "contraindicated_drugs" JSONB NOT NULL DEFAULT '[]',
    "contraindicated_foods" JSONB NOT NULL DEFAULT '[]',
    "embedding" vector(768) NOT NULL,
    "embedding_normalized" BOOL NOT NULL DEFAULT TRUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_medicine_info_drugs_gin" ON "medicine_info" USING GIN ("contraindicated_drugs");
CREATE INDEX IF NOT EXISTS "idx_medicine_info_foods_gin" ON "medicine_info" USING GIN ("contraindicated_foods");
CREATE INDEX IF NOT EXISTS "idx_medicine_info_embedding_hnsw" ON "medicine_info" USING hnsw ("embedding" vector_cosine_ops) WITH (m = 16, ef_construction = 64);
COMMENT ON COLUMN "medicine_info"."name" IS '약품명';
COMMENT ON COLUMN "medicine_info"."ingredient" IS '주성분';
COMMENT ON COLUMN "medicine_info"."usage" IS '주된 용도';
COMMENT ON COLUMN "medicine_info"."disclaimer" IS '복용 시 주의사항';
COMMENT ON COLUMN "medicine_info"."contraindicated_drugs" IS '병용 금기 약물 리스트';
COMMENT ON COLUMN "medicine_info"."contraindicated_foods" IS '병용 금기 음식 리스트';
COMMENT ON COLUMN "medicine_info"."embedding" IS '하이브리드 검색용 임베딩';
COMMENT ON COLUMN "medicine_info"."embedding_normalized" IS '임베딩 L2 정규화 여부';
COMMENT ON TABLE "medicine_info" IS 'RAG 검색을 위한 표준 약학 정보';
        COMMENT ON COLUMN "refresh_tokens"."is_revoked" IS 'Token revocation status (logout or RTR)';
        COMMENT ON COLUMN "refresh_tokens"."account_id" IS 'Token owner account';
        COMMENT ON COLUMN "refresh_tokens"."rotated_at" IS 'Token rotation timestamp (for Grace Period calculation)';
        COMMENT ON COLUMN "refresh_tokens"."token_hash" IS 'SHA-256 hash of refresh token';
        COMMENT ON COLUMN "refresh_tokens"."expires_at" IS 'Token expiration timestamp';
        COMMENT ON COLUMN "refresh_tokens"."created_at" IS 'Token issuance timestamp';
        COMMENT ON COLUMN "refresh_tokens"."replaced_by_id" IS 'ID of replacement token (for tracking)';
        COMMENT ON COLUMN "medications"."remaining_intake_count" IS 'Remaining intake count';
        COMMENT ON COLUMN "medications"."end_date" IS 'Expected end date';
        COMMENT ON COLUMN "medications"."total_intake_count" IS 'Total prescribed intake count';
        COMMENT ON COLUMN "medications"."is_active" IS 'Currently taking medication';
        COMMENT ON COLUMN "medications"."prescription_image_url" IS 'Prescription image URL';
        COMMENT ON COLUMN "medications"."intake_times" IS 'Daily intake times list';
        COMMENT ON COLUMN "medications"."start_date" IS 'Medication start date';
        COMMENT ON COLUMN "medications"."dispensed_date" IS 'Medication dispensing date';
        COMMENT ON COLUMN "medications"."expiration_date" IS 'Medication expiration date';
        COMMENT ON COLUMN "challenges"."target_days" IS 'Target completion days';
        COMMENT ON COLUMN "challenges"."title" IS 'Challenge title';
        COMMENT ON COLUMN "challenges"."completed_dates" IS 'List of completion dates';
        COMMENT ON COLUMN "challenges"."description" IS 'Detailed description';
        COMMENT ON COLUMN "intake_logs"."scheduled_date" IS 'Scheduled intake date';
        COMMENT ON COLUMN "intake_logs"."scheduled_time" IS 'Scheduled intake time';
        COMMENT ON COLUMN "intake_logs"."intake_status" IS 'Intake status';
        COMMENT ON COLUMN "intake_logs"."taken_at" IS 'Actual intake completion time';
        COMMENT ON COLUMN "drug_interaction_cache"."expires_at" IS 'Cache expiration timestamp';
        COMMENT ON COLUMN "drug_interaction_cache"."created_at" IS 'Cache creation timestamp';
        COMMENT ON COLUMN "drug_interaction_cache"."interaction" IS 'DUR interaction analysis results';
        COMMENT ON COLUMN "drug_interaction_cache"."drug_pair" IS 'Sorted drug pair key (e.g., aspirin::tylenol)';
        COMMENT ON COLUMN "llm_response_cache"."expires_at" IS 'Cache expiration timestamp';
        COMMENT ON COLUMN "llm_response_cache"."prompt_hash" IS 'SHA-256 hash of prompt';
        COMMENT ON COLUMN "llm_response_cache"."response" IS 'LLM response data';
        COMMENT ON COLUMN "llm_response_cache"."prompt_text" IS 'Original prompt text';
        COMMENT ON COLUMN "llm_response_cache"."hit_count" IS 'Cache hit count';
        COMMENT ON COLUMN "llm_response_cache"."created_at" IS 'Cache creation timestamp';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "challenges"."target_days" IS '목표 달성 일수';
        COMMENT ON COLUMN "challenges"."title" IS '챌린지 제목';
        COMMENT ON COLUMN "challenges"."completed_dates" IS '달성 완료 날짜 목록';
        COMMENT ON COLUMN "challenges"."description" IS '상세 설명';
        COMMENT ON COLUMN "intake_logs"."scheduled_date" IS '복용 예정 날짜';
        COMMENT ON COLUMN "intake_logs"."scheduled_time" IS '복용 예정 시간';
        COMMENT ON COLUMN "intake_logs"."intake_status" IS '복용 상태';
        COMMENT ON COLUMN "intake_logs"."taken_at" IS '실제 복용 완료 시간';
        COMMENT ON COLUMN "medications"."remaining_intake_count" IS '남은 복용 횟수';
        COMMENT ON COLUMN "medications"."end_date" IS '복용 종료 예정일';
        COMMENT ON COLUMN "medications"."total_intake_count" IS '처방된 총 복용 횟수';
        COMMENT ON COLUMN "medications"."is_active" IS '현재 복용 중 여부';
        COMMENT ON COLUMN "medications"."prescription_image_url" IS '처방전 이미지 URL';
        COMMENT ON COLUMN "medications"."intake_times" IS '일일 복용 시간 목록';
        COMMENT ON COLUMN "medications"."start_date" IS '복용 시작일';
        COMMENT ON COLUMN "medications"."dispensed_date" IS '약품 조제일';
        COMMENT ON COLUMN "medications"."expiration_date" IS '약품 유효기간 만료일';
        COMMENT ON COLUMN "refresh_tokens"."is_revoked" IS '토큰 무효화 여부 (로그아웃 또는 RTR 시 True)';
        COMMENT ON COLUMN "refresh_tokens"."account_id" IS '토큰 소유 계정';
        COMMENT ON COLUMN "refresh_tokens"."rotated_at" IS '토큰 교체 시점 (RTR 시 기록, Grace Period 계산용)';
        COMMENT ON COLUMN "refresh_tokens"."token_hash" IS 'Refresh Token SHA-256 해시값';
        COMMENT ON COLUMN "refresh_tokens"."expires_at" IS '토큰 만료 일시';
        COMMENT ON COLUMN "refresh_tokens"."created_at" IS '토큰 발급 일시';
        COMMENT ON COLUMN "refresh_tokens"."replaced_by_id" IS '이 토큰을 대체한 새 토큰 ID (추적용)';
        COMMENT ON COLUMN "llm_response_cache"."expires_at" IS '캐시 만료 일시';
        COMMENT ON COLUMN "llm_response_cache"."prompt_hash" IS '프롬프트 SHA-256 해시값';
        COMMENT ON COLUMN "llm_response_cache"."response" IS 'LLM 응답 데이터';
        COMMENT ON COLUMN "llm_response_cache"."prompt_text" IS '원본 프롬프트 텍스트';
        COMMENT ON COLUMN "llm_response_cache"."hit_count" IS '캐시 히트 횟수';
        COMMENT ON COLUMN "llm_response_cache"."created_at" IS '캐시 생성 일시';
        COMMENT ON COLUMN "drug_interaction_cache"."expires_at" IS '캐시 만료 일시';
        COMMENT ON COLUMN "drug_interaction_cache"."created_at" IS '캐시 생성 일시';
        COMMENT ON COLUMN "drug_interaction_cache"."interaction" IS 'DUR 상호작용 분석 결과';
        COMMENT ON COLUMN "drug_interaction_cache"."drug_pair" IS '정렬된 약품쌍 키 (예: 아스피린::타이레놀)';
        DROP TABLE IF EXISTS "medicine_info";"""


MODELS_STATE = (
    "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"
)
