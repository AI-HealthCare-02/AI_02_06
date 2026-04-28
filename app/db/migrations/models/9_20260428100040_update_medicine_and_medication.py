from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_chat_sessio_medicat_0d90b6";
        ALTER TABLE "chat_sessions" DROP CONSTRAINT IF EXISTS "fk_chat_ses_medicati_1a4ad07e";
        CREATE TABLE IF NOT EXISTS "medicine_chunk" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "section" VARCHAR(48) NOT NULL,
    "chunk_index" INT NOT NULL DEFAULT 0,
    "content" TEXT NOT NULL,
    "token_count" INT,
    "embedding" TEXT,
    "model_version" VARCHAR(64) NOT NULL,
    "interaction_tags" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "medicine_info_id" INT NOT NULL REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_medicine_ch_medicin_e873e2" UNIQUE ("medicine_info_id", "section", "chunk_index")
);
CREATE INDEX IF NOT EXISTS "idx_medicine_ch_medicin_68dcca" ON "medicine_chunk" ("medicine_info_id");
CREATE INDEX IF NOT EXISTS "idx_medicine_ch_section_af179e" ON "medicine_chunk" ("section");
CREATE INDEX IF NOT EXISTS "idx_medicine_ch_model_v_6d67cd" ON "medicine_chunk" ("model_version");
COMMENT ON COLUMN "medicine_chunk"."section" IS 'Chunk section tag (MedicineChunkSection)';
COMMENT ON COLUMN "medicine_chunk"."chunk_index" IS 'Sub-chunk order when ARTICLE is split by token limit';
COMMENT ON COLUMN "medicine_chunk"."content" IS 'Final embedding-target text with header prefix';
COMMENT ON COLUMN "medicine_chunk"."token_count" IS 'Token count for monitoring';
COMMENT ON COLUMN "medicine_chunk"."embedding" IS 'pgvector VECTOR(768) - materialised via manual SQL';
COMMENT ON COLUMN "medicine_chunk"."model_version" IS 'Embedding model version (e.g. ko-sroberta-multitask-v1)';
COMMENT ON COLUMN "medicine_chunk"."interaction_tags" IS 'JSONB array of interaction tags (see interaction_tags.json)';
COMMENT ON COLUMN "medicine_chunk"."medicine_info_id" IS 'Parent medicine_info reference';
COMMENT ON TABLE "medicine_chunk" IS 'Section-level embedding chunks for RAG similarity search';
        CREATE TABLE IF NOT EXISTS "medicine_ingredient" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "mtral_sn" INT NOT NULL,
    "mtral_code" VARCHAR(16),
    "mtral_name" VARCHAR(128) NOT NULL,
    "main_ingr_eng" VARCHAR(256),
    "quantity" VARCHAR(32),
    "unit" VARCHAR(16),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "medicine_info_id" INT NOT NULL REFERENCES "medicine_info" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_medicine_in_medicin_8f85f4" UNIQUE ("medicine_info_id", "mtral_sn")
);
CREATE INDEX IF NOT EXISTS "idx_medicine_in_mtral_n_3e3034" ON "medicine_ingredient" ("mtral_name");
CREATE INDEX IF NOT EXISTS "idx_medicine_in_mtral_c_705f45" ON "medicine_ingredient" ("mtral_code");
COMMENT ON COLUMN "medicine_ingredient"."mtral_sn" IS 'Ingredient sequence number within the drug (API MTRAL_SN)';
COMMENT ON COLUMN "medicine_ingredient"."mtral_code" IS 'Ingredient standard code (API MTRAL_CODE)';
COMMENT ON COLUMN "medicine_ingredient"."mtral_name" IS 'Korean ingredient name (API MTRAL_NM)';
COMMENT ON COLUMN "medicine_ingredient"."main_ingr_eng" IS 'English ingredient name (API MAIN_INGR_ENG)';
COMMENT ON COLUMN "medicine_ingredient"."quantity" IS 'Ingredient quantity (API QNT)';
COMMENT ON COLUMN "medicine_ingredient"."unit" IS 'Quantity unit (API INGD_UNIT_CD)';
COMMENT ON COLUMN "medicine_ingredient"."medicine_info_id" IS 'Parent medicine_info reference';
COMMENT ON TABLE "medicine_ingredient" IS 'Drug active ingredients (1:N from medicine_info)';
        CREATE TABLE IF NOT EXISTS "data_sync_log" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "sync_type" VARCHAR(32) NOT NULL,
    "sync_date" TIMESTAMPTZ NOT NULL,
    "total_fetched" INT NOT NULL DEFAULT 0,
    "total_inserted" INT NOT NULL DEFAULT 0,
    "total_updated" INT NOT NULL DEFAULT 0,
    "status" VARCHAR(16) NOT NULL,
    "error_message" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_data_sync_l_sync_ty_af36c6" ON "data_sync_log" ("sync_type", "status");
COMMENT ON COLUMN "data_sync_log"."sync_type" IS 'Sync target type (e.g. medicine_info)';
COMMENT ON COLUMN "data_sync_log"."sync_date" IS 'Sync execution timestamp';
COMMENT ON COLUMN "data_sync_log"."total_fetched" IS 'Total records fetched from API';
COMMENT ON COLUMN "data_sync_log"."total_inserted" IS 'Number of newly inserted records';
COMMENT ON COLUMN "data_sync_log"."total_updated" IS 'Number of updated existing records';
COMMENT ON COLUMN "data_sync_log"."status" IS 'Sync result status (SUCCESS / FAILED)';
COMMENT ON COLUMN "data_sync_log"."error_message" IS 'Error details when sync fails';
COMMENT ON TABLE "data_sync_log" IS 'Public API data synchronization history';
        CREATE TABLE IF NOT EXISTS "ocr_drafts" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(16) NOT NULL DEFAULT 'pending',
    "medicines" JSONB NOT NULL,
    "filename" VARCHAR(256),
    "image_hash" VARCHAR(64) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "processed_at" TIMESTAMPTZ,
    "consumed_at" TIMESTAMPTZ,
    "profile_id" UUID NOT NULL REFERENCES "profiles" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "ocr_drafts"."status" IS 'pending / ready / no_text / no_candidates / failed';
COMMENT ON COLUMN "ocr_drafts"."medicines" IS 'ExtractedMedicine 리스트 (ai-worker 가 채움)';
COMMENT ON COLUMN "ocr_drafts"."filename" IS '원본 파일명';
COMMENT ON COLUMN "ocr_drafts"."image_hash" IS 'SHA256(image_bytes) — dedup 키';
COMMENT ON COLUMN "ocr_drafts"."processed_at" IS 'ai-worker 처리 완료 시각';
COMMENT ON COLUMN "ocr_drafts"."consumed_at" IS 'confirm 완료 시각 (NULL=활성)';
COMMENT ON COLUMN "ocr_drafts"."profile_id" IS '업로드 프로필';
COMMENT ON TABLE "ocr_drafts" IS '처방전 OCR 처리 결과 임시 저장 (24h, profile 별 회수 가능)';
        ALTER TABLE "medications" DROP COLUMN "prescription_image_url";
        ALTER TABLE "medicine_info" ADD "nb_doc_url" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD "storage_method" TEXT;
        ALTER TABLE "medicine_info" ADD "main_item_ingr" TEXT;
        ALTER TABLE "medicine_info" ADD "item_seq" VARCHAR(20) UNIQUE;
        ALTER TABLE "medicine_info" ADD "permit_date" VARCHAR(8);
        ALTER TABLE "medicine_info" ADD "chart" TEXT;
        ALTER TABLE "medicine_info" ADD "spclty_pblc" VARCHAR(32);
        ALTER TABLE "medicine_info" ADD "entp_name" VARCHAR(128);
        ALTER TABLE "medicine_info" ADD "ee_doc_url" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD "material_name" TEXT;
        ALTER TABLE "medicine_info" ADD "cancel_name" VARCHAR(16);
        ALTER TABLE "medicine_info" ADD "item_eng_name" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD "atc_code" VARCHAR(32);
        ALTER TABLE "medicine_info" ADD "change_date" VARCHAR(8);
        ALTER TABLE "medicine_info" ADD "valid_term" VARCHAR(64);
        ALTER TABLE "medicine_info" ADD "ud_doc_url" VARCHAR(256);
        ALTER TABLE "medicine_info" ADD "pack_unit" VARCHAR(2048);
        ALTER TABLE "medicine_info" ADD "last_synced_at" TIMESTAMPTZ;
        ALTER TABLE "medicine_info" ADD "ee_doc_data" TEXT;
        ALTER TABLE "medicine_info" ADD "nb_doc_data" TEXT;
        ALTER TABLE "medicine_info" ADD "product_type" VARCHAR(64);
        ALTER TABLE "medicine_info" ADD "ud_doc_data" TEXT;
        ALTER TABLE "medicine_info" ADD "bizrno" VARCHAR(16);
        ALTER TABLE "medicine_info" ADD "edi_code" VARCHAR(256);
        ALTER TABLE "medicine_info" DROP COLUMN "embedding";
        COMMENT ON COLUMN "medicine_info"."efficacy" IS 'Drug efficacy and effects';
        ALTER TABLE "medicine_info" ALTER COLUMN "medicine_name" TYPE VARCHAR(200) USING "medicine_name"::VARCHAR(200);
        COMMENT ON COLUMN "medicine_info"."medicine_name" IS 'Drug product name in Korean';
        COMMENT ON COLUMN "medicine_info"."category" IS 'Drug category for search filtering';
        COMMENT ON COLUMN "medicine_info"."side_effects" IS 'Known side effects';
        COMMENT ON COLUMN "medicine_info"."precautions" IS 'Usage precautions';
        ALTER TABLE "lifestyle_guides" ADD "processed_at" TIMESTAMPTZ;
        ALTER TABLE "lifestyle_guides" ADD "status" VARCHAR(16) NOT NULL DEFAULT 'pending';
        ALTER TABLE "chat_sessions" DROP COLUMN "medication_id";
        ALTER TABLE "messages" ADD "metadata" JSONB NOT NULL;
        COMMENT ON COLUMN "medicine_info"."nb_doc_url" IS 'Precaution PDF source URL (NB_DOC_ID)';
COMMENT ON COLUMN "medicine_info"."storage_method" IS 'Storage method and instructions';
COMMENT ON COLUMN "medicine_info"."main_item_ingr" IS 'Active ingredients with standard codes';
COMMENT ON COLUMN "medicine_info"."item_seq" IS 'Drug product code from public API (UPSERT key)';
COMMENT ON COLUMN "medicine_info"."permit_date" IS 'Permit date in YYYYMMDD format';
COMMENT ON COLUMN "medicine_info"."chart" IS 'Physical appearance (CHART)';
COMMENT ON COLUMN "medicine_info"."spclty_pblc" IS 'Professional or OTC drug classification';
COMMENT ON COLUMN "medicine_info"."entp_name" IS 'Manufacturer name';
COMMENT ON COLUMN "medicine_info"."ee_doc_url" IS 'Efficacy PDF source URL (EE_DOC_ID)';
COMMENT ON COLUMN "medicine_info"."material_name" IS 'Total/portion raw string (MATERIAL_NAME)';
COMMENT ON COLUMN "medicine_info"."cancel_name" IS 'Current status (normal or cancelled)';
COMMENT ON COLUMN "medicine_info"."item_eng_name" IS 'Drug product name in English';
COMMENT ON COLUMN "medicine_info"."atc_code" IS 'WHO ATC classification code (ATC_CODE)';
COMMENT ON COLUMN "medicine_info"."change_date" IS 'Last change date from API in YYYYMMDD format';
COMMENT ON COLUMN "medicine_info"."valid_term" IS 'Shelf-life description (VALID_TERM)';
COMMENT ON COLUMN "medicine_info"."ud_doc_url" IS 'Usage PDF source URL (UD_DOC_ID)';
COMMENT ON COLUMN "medicine_info"."pack_unit" IS 'Packaging unit description (PACK_UNIT) — 일부 품목은 256 자 초과 가능';
COMMENT ON COLUMN "medicine_info"."last_synced_at" IS 'Last synchronization timestamp from public API';
COMMENT ON COLUMN "medicine_info"."ee_doc_data" IS 'Raw EE_DOC_DATA XML (효능효과 원문)';
COMMENT ON COLUMN "medicine_info"."nb_doc_data" IS 'Raw NB_DOC_DATA XML (사용상주의사항 원문)';
COMMENT ON COLUMN "medicine_info"."product_type" IS 'Product classification code';
COMMENT ON COLUMN "medicine_info"."ud_doc_data" IS 'Raw UD_DOC_DATA XML (용법용량 원문)';
COMMENT ON COLUMN "medicine_info"."bizrno" IS 'Business registration number';
COMMENT ON COLUMN "medicine_info"."edi_code" IS 'Insurance billing codes (comma-separated)';
COMMENT ON COLUMN "lifestyle_guides"."processed_at" IS 'Terminal-status set time';
COMMENT ON COLUMN "lifestyle_guides"."status" IS 'Async generation status (pending/ready/no_active_meds/failed)';
COMMENT ON COLUMN "messages"."metadata" IS 'RAG debug/audit metadata (intent, medicine_names, scores, token usage)';
        DROP TABLE IF EXISTS "drug_interaction_cache";
        DROP TABLE IF EXISTS "llm_response_cache";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_medicine_in_item_se_f02f47";
        ALTER TABLE "medications" ADD "prescription_image_url" VARCHAR(512);
        ALTER TABLE "messages" DROP COLUMN "metadata";
        ALTER TABLE "chat_sessions" ADD "medication_id" UUID;
        ALTER TABLE "medicine_info" ADD "embedding" TEXT;
        ALTER TABLE "medicine_info" DROP COLUMN "nb_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN "storage_method";
        ALTER TABLE "medicine_info" DROP COLUMN "main_item_ingr";
        ALTER TABLE "medicine_info" DROP COLUMN "item_seq";
        ALTER TABLE "medicine_info" DROP COLUMN "permit_date";
        ALTER TABLE "medicine_info" DROP COLUMN "chart";
        ALTER TABLE "medicine_info" DROP COLUMN "spclty_pblc";
        ALTER TABLE "medicine_info" DROP COLUMN "entp_name";
        ALTER TABLE "medicine_info" DROP COLUMN "ee_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN "material_name";
        ALTER TABLE "medicine_info" DROP COLUMN "cancel_name";
        ALTER TABLE "medicine_info" DROP COLUMN "item_eng_name";
        ALTER TABLE "medicine_info" DROP COLUMN "atc_code";
        ALTER TABLE "medicine_info" DROP COLUMN "change_date";
        ALTER TABLE "medicine_info" DROP COLUMN "valid_term";
        ALTER TABLE "medicine_info" DROP COLUMN "ud_doc_url";
        ALTER TABLE "medicine_info" DROP COLUMN "pack_unit";
        ALTER TABLE "medicine_info" DROP COLUMN "last_synced_at";
        ALTER TABLE "medicine_info" DROP COLUMN "ee_doc_data";
        ALTER TABLE "medicine_info" DROP COLUMN "nb_doc_data";
        ALTER TABLE "medicine_info" DROP COLUMN "product_type";
        ALTER TABLE "medicine_info" DROP COLUMN "ud_doc_data";
        ALTER TABLE "medicine_info" DROP COLUMN "bizrno";
        ALTER TABLE "medicine_info" DROP COLUMN "edi_code";
        COMMENT ON COLUMN "medicine_info"."efficacy" IS NULL;
        COMMENT ON COLUMN "medicine_info"."medicine_name" IS NULL;
        ALTER TABLE "medicine_info" ALTER COLUMN "medicine_name" TYPE VARCHAR(128) USING "medicine_name"::VARCHAR(128);
        COMMENT ON COLUMN "medicine_info"."category" IS NULL;
        COMMENT ON COLUMN "medicine_info"."side_effects" IS NULL;
        COMMENT ON COLUMN "medicine_info"."precautions" IS NULL;
        ALTER TABLE "lifestyle_guides" DROP COLUMN "processed_at";
        ALTER TABLE "lifestyle_guides" DROP COLUMN "status";
        COMMENT ON COLUMN "medications"."prescription_image_url" IS 'Prescription image URL';
        DROP TABLE IF EXISTS "ocr_drafts";
        DROP TABLE IF EXISTS "data_sync_log";
        DROP TABLE IF EXISTS "medicine_chunk";
        DROP TABLE IF EXISTS "medicine_ingredient";
        ALTER TABLE "chat_sessions" ADD CONSTRAINT "fk_chat_ses_medicati_1a4ad07e" FOREIGN KEY ("medication_id") REFERENCES "medications" ("id") ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS "idx_chat_sessio_medicat_0d90b6" ON "chat_sessions" ("medication_id");"""


MODELS_STATE = (
    "eJztfXtz4kiy71ep4J/FcWw3xmBj4u6JoG26m9t+rbF3957xBiOkAnRaSIwkupvZ2O9+M+"
    "shlV5Y4mFkNxMT3Y1UWar6ZT0ys7Iy/12ZOga1vOMOdU19UmmTf1dsbUrhH7E3h6SizWbh"
    "c3zga0OLFdXCMkPPdzXdh6cjzfIoPDKop7vmzDcdG57ac8vCh44OBU17HD6a2+YfczrwnT"
    "H1J9SFF7/9Cx6btkF/Uk/+nH0bjExqGZGmmgZ+mz0f+IsZe9az/U+sIH5tONAdaz61w8Kz"
    "hT9x7KC0afv4dExt6mo+xep9d47Nx9aJfsoe8ZaGRXgTFRqDjrS55SvdzYmB7tiIH7TGYx"
    "0c41eO6ieN80br9KzRgiKsJcGT8//w7oV954QMgdvHyn/Ye83XeAkGY4jbd+p62KQEeJcT"
    "zU1HTyGJQQgNj0MoAVuGoXwQghgOnA2hONV+Dixqj30c4PVmcwlmf+88XH7pPFSh1AH2xo"
    "HBzMf4rXhV5+8Q2BBInBoFQBTF3yaAJ7VaDgChVCaA7F0UQPiiT/kcjIL4f/t3t+kgKiQx"
    "IJ9s6OBvhqn7h8QyPf9f5YR1CYrYa2z01PP+sFTwqjedf8Zxvby++8hQcDx/7LJaWAUfAW"
    "NcMkfflMmPD4aa/u2H5hqDxBun7mSVTb6a1qfxJ5qtjRlW2GPsn9xEdN2Z237q/iJeLd9g"
    "eCEv1xZTEVUSVhEZOS7xfAdZQeYedYk2h/3F9k1dQwJi2lBiyv59XIkxbo2qnu1n+3Fieo"
    "IUyahHPEc3NYtYzti0l1ATzTbIRPOe7ZP2LXGpxZ56E3PmkR+mPyEz1xmZFvUOiT7R/IFH"
    "PVyV4ScSunQE35rAVvqN2h5rSceHLg3nPvXazzaB/0yjTe5dc6q5C/KNLsjTU+/qmL/CZg"
    "3gA99Ng7pt0om2Ur4g1a+dr527Q3Lb+Xv34UDQyrcDwbEBfkeC2LsiI9eZEqgvKCjobFP/"
    "hgOjTZ4A1794wYOwXuzvABo8poO5a0HBh2vijBgfoLwoQFgBQWR60Azf/A61/mPChAr2ad"
    "E0eE34a1FcdymuDwPND5vMnmG3fXNKPV+bzkTh+cwICl9rni8eJMoB76ks13dGPn8QrbGS"
    "Lv38Volwgk3xJLyVf60jJSHbC4hJ87lpHCPNKivqy9JS5f+M5rbO0GFfwj8a/13ZyhLLVt"
    "PTs4P4ysl6t1xsSrAlue937fmU4dqD9mi2TpMyQIK3u5UGKmw6twn769lms7rNJ3d8Vcwl"
    "JZzlERLOsmWEs7iIkDb2C8hcGeRvVAart/LAW29l44vvogDLJbcIqirN24TytJ4DydN6Jp"
    "D4KjFQo3tVwWGaJF4JWbG67gzY5kkeZKFUJrTsXRTbYEtPYvrRcSyq2Rm7mUoXg3MIhOUc"
    "qUvw+3h3dx3RED72HmM4Pt187MIiwOCFQqbP7SLCKqDoXoHckwT1Ct6goJKhgkUoY7Aagv"
    "RY/qOcGFegD8adbS3ElFmC+WPvptt/7NzcR4C/6jx28U2dPV3EnlbjW1xQCflH7/ELwZ/k"
    "f+5uu3E5JCj3+D8VbBPIC87Adn4MNEORneRTCUyEsaGMWpSxUco9Y3fKWNH4kK+hTlGUr1"
    "HKDfD19TeZN8JG2e3EBC1gkQk5HtXoU/Y+Qf/p64OwFaTwVxhcHnhdj1jV62oY7JPE+WGj"
    "5SQ0++Tmefg0bVZIk8h66NzzWsq5pOXCIWIQWg8MEFP9Pq/pjQGyTWNmZAKlWDTjEyzbrJ"
    "mc1i8bN0XthNEQ3sgplSbKpAXzhfIxMyV/70kTIqcSNkdqT9CSYRCP6nPX9BdkBOLf3GU2"
    "xSPS5xbO/pfOUb15htbLCfmuWXN45sAuTKq24xPHNcemrVmi4gMk7E2n1DDReGbaQGAa3O"
    "IG/1vO2Jn7pArSu0u/A4VB/koegb+M7gZGkHlk0O+mToVF1ZvPZo4LFFN8N7Oo7MAsXHIY"
    "7cPjQ5v0PA9bZ9MfAp3/CluArbYM8RztUR5Fus/AHEruqWs6Rpt80WwDVhwC4w8QcRFVl8"
    "LY93yPVOtHgJNjG4TViHBpIx+a4To+6+BBLrssmpx5I1yozTWkjZb3pU0+Aejm2GZlfYdE"
    "7NWiLCMfID/aUe44oyifRXn6c2bCQ2ay5Es2e5JuBw1ZIwvjT2ErhoL+HKAQfISuAO7SVM"
    "xwEJZRQSmQCT9Cqth/FXSia5Y+5wtXUBOdWVDCGAwXzN7cu+JdY0/ZWOcIsspwen2DuXGQ"
    "YvXlzTBhWOBAf9lCG7O8/laJ2pZCbLiRNrdV9qM5LvHxdeVRGY+E24Jzn2Vf1Ounp+f12u"
    "lZq9k4P2+2asGhdvLVstPtj73PqMpGZLeXT7zDuVDEKBOl2padKyf6S6fwKqbas0YOO81Z"
    "I9NMg6+iFoVwBSmqoEQpS6V4VrLXwkJS7JvVXGJ2OLm0JVevFwxxCuErWuIyxKmce9baHN"
    "6gvS7cOIvOrihlmdT/yooSwK8386LCTjHZIUn7shyxVa7nk9TKJ2C8c+N5JUsQzsmJ92J5"
    "Tc6+ZWfP2b4US4+c1/Kp2J0xbgWfioTpM4FrElSh336li4Q7RbrNSvEneztgJgxY8NjVfg"
    "TqYmwEQa+5JZ+B3ulfdq66lf/sxrVPGkxTDGGKLTXbBqaabV+2fokqM/3xbAMop6a1IFM6"
    "HcKTpd59a9WW7uAX+KEpznxYMVbosRr9CTXdaL3e4bNt2ro1N/DbqrsfYROMuwNSzfInxJ"
    "u73+mCoIZb3LOvgNVItoLNrzZ5iDeKVPvd60+H5L7z0L19PCSXX3rXV4eE+vqxNK1whz4J"
    "suLNx7sy4F1pE3RWJWy4MahSOxo31chad+mg94L5J4JgQQvQ3i8vYw85XGLciQKewDSfX1"
    "6ikl375eE0g6EJfz7bfLK1xaR7ttmka/O592z37++e+l0oy/5+tu8ev6APH/trFcPQ5n34"
    "CruX7V3LIvhFFs4kkNmXJRKEG7gyUaqz/43dmHj3yt2v50Cz94x6p4zde0a9Vyvnu7GzvI"
    "JI/G7NKmu7AR1u1Iqi2DeoIa7DrelgdRNU9LaAjcxVyxyBnryw6GAMU2xdB7xrWdtnrOx1"
    "VS32SWHGm4XGqw3h5C2mM9+ZDixnvCZGV5ppLfq8umtn/LogwQe3BpE+0SxUn9YdRJeynj"
    "c8rfZ+nDFA4LH2jW5g+vRYRa89cTYLhqO7A8PVRv6aWNzp7hVW87pryPNcb+rN5/mw1dTh"
    "z4ahk+e50aw15COj2Wisua5s89BD2bdTzj2iu3r20UdMjHj59COsWDmymLlhoeDMPHnWUY"
    "A262RDKRs2PXLSER5iGI4H0LFzDZxsxNMn1JiziAV4mBGpzKA+bGjFAxWI/SdxnBE51hFl"
    "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"
    "V82otQV435yL3n/+P/xfA9Y="
)
