from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(40) NOT NULL,
    "hashed_password" VARCHAR(128) NOT NULL,
    "name" VARCHAR(20) NOT NULL,
    "gender" VARCHAR(16) NOT NULL,
    "birthday" DATE NOT NULL,
    "phone_number" VARCHAR(11) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "last_login" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gender" IS 'MALE: MALE\nFEMALE: FEMALE';
CREATE TABLE IF NOT EXISTS "accounts" (
    "id" UUID NOT NULL PRIMARY KEY,
    "auth_provider" VARCHAR(16) NOT NULL,
    "provider_account_id" VARCHAR(128) NOT NULL,
    "email" VARCHAR(255),
    "nickname" VARCHAR(32) NOT NULL,
    "is_active" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
COMMENT ON COLUMN "accounts"."auth_provider" IS 'KAKAO: KAKAO\nNAVER: NAVER';
CREATE TABLE IF NOT EXISTS "refresh_tokens" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "token_hash" VARCHAR(64) NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "is_revoked" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "account_id" UUID NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_token_h_e92003" ON "refresh_tokens" ("token_hash");
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_account_b96f59" ON "refresh_tokens" ("account_id", "is_revoked");
COMMENT ON COLUMN "refresh_tokens"."id" IS '토큰 레코드 ID';
COMMENT ON COLUMN "refresh_tokens"."token_hash" IS 'Refresh Token SHA-256 해시값';
COMMENT ON COLUMN "refresh_tokens"."expires_at" IS '토큰 만료 일시';
COMMENT ON COLUMN "refresh_tokens"."is_revoked" IS '토큰 무효화 여부 (로그아웃 시 True)';
COMMENT ON COLUMN "refresh_tokens"."created_at" IS '토큰 발급 일시';
COMMENT ON COLUMN "refresh_tokens"."account_id" IS '토큰 소유 계정';
COMMENT ON TABLE "refresh_tokens" IS 'Refresh Token 관리 모델';
CREATE TABLE IF NOT EXISTS "profiles" (
    "id" UUID NOT NULL PRIMARY KEY,
    "relation_type" VARCHAR(16) NOT NULL,
    "name" VARCHAR(32) NOT NULL,
    "health_survey" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "account_id" UUID NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "profiles"."relation_type" IS 'SELF: SELF\nPARENT: PARENT\nCHILD: CHILD\nSPOUSE: SPOUSE\nOTHER: OTHER';
CREATE TABLE IF NOT EXISTS "medications" (
    "id" UUID NOT NULL PRIMARY KEY,
    "medicine_name" VARCHAR(128) NOT NULL,
    "dose_per_intake" VARCHAR(32),
    "intake_instruction" VARCHAR(256),
    "intake_times" JSONB NOT NULL,
    "total_intake_count" INT NOT NULL,
    "remaining_intake_count" INT NOT NULL,
    "start_date" DATE NOT NULL,
    "end_date" DATE,
    "dispensed_date" DATE,
    "expiration_date" DATE,
    "prescription_image_url" VARCHAR(512),
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_medications_profile_c1211f" ON "medications" ("profile_id", "is_active");
COMMENT ON COLUMN "medications"."medicine_name" IS '약품명';
COMMENT ON COLUMN "medications"."dose_per_intake" IS '1회 복용량 (예: 1정, 5ml)';
COMMENT ON COLUMN "medications"."intake_instruction" IS '복용 지시사항';
COMMENT ON COLUMN "medications"."intake_times" IS '일일 복용 시간 목록';
COMMENT ON COLUMN "medications"."total_intake_count" IS '처방된 총 복용 횟수';
COMMENT ON COLUMN "medications"."remaining_intake_count" IS '남은 복용 횟수';
COMMENT ON COLUMN "medications"."start_date" IS '복용 시작일';
COMMENT ON COLUMN "medications"."end_date" IS '복용 종료 예정일';
COMMENT ON COLUMN "medications"."dispensed_date" IS '약품 조제일';
COMMENT ON COLUMN "medications"."expiration_date" IS '약품 유효기간 만료일';
COMMENT ON COLUMN "medications"."prescription_image_url" IS '처방전 이미지 URL';
COMMENT ON COLUMN "medications"."is_active" IS '현재 복용 중 여부';
CREATE TABLE IF NOT EXISTS "challenges" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(64) NOT NULL,
    "description" VARCHAR(256),
    "target_days" INT NOT NULL,
    "completed_dates" JSONB NOT NULL,
    "challenge_status" VARCHAR(16) NOT NULL DEFAULT 'IN_PROGRESS',
    "started_date" DATE NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_challenges_profile_281206" ON "challenges" ("profile_id", "challenge_status");
COMMENT ON COLUMN "challenges"."title" IS '챌린지 제목';
COMMENT ON COLUMN "challenges"."description" IS '상세 설명';
COMMENT ON COLUMN "challenges"."target_days" IS '목표 달성 일수';
COMMENT ON COLUMN "challenges"."completed_dates" IS '달성 완료 날짜 목록';
COMMENT ON COLUMN "challenges"."challenge_status" IS '진행 상태';
COMMENT ON COLUMN "challenges"."started_date" IS '챌린지 시작 날짜';
CREATE TABLE IF NOT EXISTS "chat_sessions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(64),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "account_id" UUID NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE,
    "medication_id" UUID REFERENCES "medications" ("id") ON DELETE CASCADE,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chat_sessio_account_4a006a" ON "chat_sessions" ("account_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_chat_sessio_profile_ab074b" ON "chat_sessions" ("profile_id");
CREATE INDEX IF NOT EXISTS "idx_chat_sessio_medicat_0d90b6" ON "chat_sessions" ("medication_id");
CREATE TABLE IF NOT EXISTS "messages" (
    "id" UUID NOT NULL PRIMARY KEY,
    "sender_type" VARCHAR(16) NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "session_id" UUID NOT NULL REFERENCES "chat_sessions" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_messages_session_78394c" ON "messages" ("session_id", "created_at");
COMMENT ON COLUMN "messages"."sender_type" IS 'USER: USER\nASSISTANT: ASSISTANT';
CREATE TABLE IF NOT EXISTS "message_feedbacks" (
    "id" UUID NOT NULL PRIMARY KEY,
    "is_helpful" BOOL NOT NULL,
    "feedback_text" VARCHAR(256),
    "metadata" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "message_id" UUID NOT NULL UNIQUE REFERENCES "messages" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "intake_logs" (
    "id" UUID NOT NULL PRIMARY KEY,
    "scheduled_date" DATE NOT NULL,
    "scheduled_time" TIMETZ NOT NULL,
    "intake_status" VARCHAR(16) NOT NULL DEFAULT 'SCHEDULED',
    "taken_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "medication_id" UUID NOT NULL REFERENCES "medications" ("id") ON DELETE CASCADE,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_intake_logs_profile_ab6b26" ON "intake_logs" ("profile_id", "scheduled_date");
CREATE INDEX IF NOT EXISTS "idx_intake_logs_schedul_5eb536" ON "intake_logs" ("scheduled_date", "intake_status");
COMMENT ON COLUMN "intake_logs"."scheduled_date" IS '복용 예정 날짜';
COMMENT ON COLUMN "intake_logs"."scheduled_time" IS '복용 예정 시간';
COMMENT ON COLUMN "intake_logs"."intake_status" IS '복용 상태';
COMMENT ON COLUMN "intake_logs"."taken_at" IS '실제 복용 완료 시간';
CREATE TABLE IF NOT EXISTS "drug_interaction_cache" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "drug_pair" VARCHAR(256) NOT NULL UNIQUE,
    "interaction" JSONB NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_drug_intera_drug_pa_abfbd4" ON "drug_interaction_cache" ("drug_pair");
CREATE INDEX IF NOT EXISTS "idx_drug_intera_expires_b14542" ON "drug_interaction_cache" ("expires_at");
COMMENT ON COLUMN "drug_interaction_cache"."id" IS '캐시 레코드 ID';
COMMENT ON COLUMN "drug_interaction_cache"."drug_pair" IS '정렬된 약품쌍 키 (예: 아스피린::타이레놀)';
COMMENT ON COLUMN "drug_interaction_cache"."interaction" IS 'DUR 상호작용 분석 결과';
COMMENT ON COLUMN "drug_interaction_cache"."expires_at" IS '캐시 만료 일시';
COMMENT ON COLUMN "drug_interaction_cache"."created_at" IS '캐시 생성 일시';
COMMENT ON TABLE "drug_interaction_cache" IS 'DUR 병용금기 캐시 모델';
CREATE TABLE IF NOT EXISTS "llm_response_cache" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "prompt_hash" VARCHAR(64) NOT NULL UNIQUE,
    "prompt_text" TEXT NOT NULL,
    "response" JSONB NOT NULL,
    "hit_count" INT NOT NULL DEFAULT 0,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_llm_respons_prompt__2d135a" ON "llm_response_cache" ("prompt_hash");
CREATE INDEX IF NOT EXISTS "idx_llm_respons_expires_418e4a" ON "llm_response_cache" ("expires_at");
COMMENT ON COLUMN "llm_response_cache"."id" IS '캐시 레코드 ID';
COMMENT ON COLUMN "llm_response_cache"."prompt_hash" IS '프롬프트 SHA-256 해시값';
COMMENT ON COLUMN "llm_response_cache"."prompt_text" IS '원본 프롬프트 텍스트';
COMMENT ON COLUMN "llm_response_cache"."response" IS 'LLM 응답 데이터';
COMMENT ON COLUMN "llm_response_cache"."hit_count" IS '캐시 히트 횟수';
COMMENT ON COLUMN "llm_response_cache"."expires_at" IS '캐시 만료 일시';
COMMENT ON COLUMN "llm_response_cache"."created_at" IS '캐시 생성 일시';
COMMENT ON TABLE "llm_response_cache" IS 'LLM 응답 캐시 모델';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "qWo4AY58aG2lCVaaYKUJVppgAZrgz/8DIx676g=="
)
