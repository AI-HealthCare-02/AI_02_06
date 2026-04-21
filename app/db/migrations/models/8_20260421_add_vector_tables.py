"""Add vector tables for RAG system.

This migration creates tables for pgvector-based RAG functionality:
- pharmaceutical_documents: Main document storage
- document_chunks: Chunked documents with embeddings
- search_queries: Query analytics
- embedding_models: Model configuration tracking

NOTE: This migration requires pgvector extension to be installed.
The docker-compose uses ankane/pgvector image which includes pgvector.
"""

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    -- Enable pgvector extension
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Create pharmaceutical_documents table
    CREATE TABLE IF NOT EXISTS "pharmaceutical_documents" (
        "id" SERIAL NOT NULL PRIMARY KEY,
        "title" VARCHAR(500) NOT NULL,
        "document_type" VARCHAR(20) NOT NULL,
        "source_url" TEXT,
        "content" TEXT NOT NULL,
        "content_hash" VARCHAR(64) NOT NULL UNIQUE,
        "medicine_names" JSONB NOT NULL DEFAULT '[]',
        "target_conditions" JSONB NOT NULL DEFAULT '[]',
        "language" VARCHAR(10) NOT NULL DEFAULT 'ko',
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "last_indexed_at" TIMESTAMPTZ,
        "document_embedding" vector(768)
    );

    -- Create indexes for pharmaceutical_documents
    CREATE INDEX IF NOT EXISTS "idx_pharma_docs_type_created"
        ON "pharmaceutical_documents" ("document_type", "created_at");
    CREATE INDEX IF NOT EXISTS "idx_pharma_docs_medicine_names"
        ON "pharmaceutical_documents" USING GIN ("medicine_names");
    CREATE INDEX IF NOT EXISTS "idx_pharma_docs_target_conditions"
        ON "pharmaceutical_documents" USING GIN ("target_conditions");

    -- Create document_chunks table
    CREATE TABLE IF NOT EXISTS "document_chunks" (
        "id" SERIAL NOT NULL PRIMARY KEY,
        "document_id" INT NOT NULL REFERENCES "pharmaceutical_documents" ("id") ON DELETE CASCADE,
        "chunk_index" INT NOT NULL,
        "chunk_type" VARCHAR(20) NOT NULL,
        "content" TEXT NOT NULL,
        "content_hash" VARCHAR(64) NOT NULL,
        "section_title" VARCHAR(200),
        "word_count" INT NOT NULL,
        "char_count" INT NOT NULL,
        "keywords" JSONB NOT NULL DEFAULT '[]',
        "medicine_names" JSONB NOT NULL DEFAULT '[]',
        "dosage_info" JSONB NOT NULL DEFAULT '{}',
        "target_conditions" JSONB NOT NULL DEFAULT '[]',
        "contraindicated_conditions" JSONB NOT NULL DEFAULT '[]',
        "embedding" vector(768) NOT NULL,
        "embedding_normalized" BOOLEAN NOT NULL DEFAULT FALSE,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT "uidx_document_chunk" UNIQUE ("document_id", "chunk_index")
    );

    -- Create indexes for document_chunks
    CREATE INDEX IF NOT EXISTS "idx_chunks_type_created"
        ON "document_chunks" ("chunk_type", "created_at");
    CREATE INDEX IF NOT EXISTS "idx_chunks_medicine_names"
        ON "document_chunks" USING GIN ("medicine_names");
    CREATE INDEX IF NOT EXISTS "idx_chunks_keywords"
        ON "document_chunks" USING GIN ("keywords");
    CREATE INDEX IF NOT EXISTS "idx_chunks_target_conditions"
        ON "document_chunks" USING GIN ("target_conditions");

    -- Create HNSW index for vector similarity search (faster than IVFFlat for small-medium datasets)
    CREATE INDEX IF NOT EXISTS "idx_chunks_embedding_hnsw"
        ON "document_chunks" USING hnsw ("embedding" vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

    -- Create search_queries table for analytics
    CREATE TABLE IF NOT EXISTS "search_queries" (
        "id" SERIAL NOT NULL PRIMARY KEY,
        "query_text" TEXT NOT NULL,
        "query_embedding" vector(768),
        "search_type" VARCHAR(50) NOT NULL,
        "filters_applied" JSONB NOT NULL DEFAULT '{}',
        "results_count" INT NOT NULL,
        "top_chunk_ids" JSONB NOT NULL DEFAULT '[]',
        "search_duration_ms" INT NOT NULL,
        "user_profile_id" INT,
        "user_conditions" JSONB NOT NULL DEFAULT '[]',
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for search_queries
    CREATE INDEX IF NOT EXISTS "idx_search_queries_created"
        ON "search_queries" ("created_at");
    CREATE INDEX IF NOT EXISTS "idx_search_queries_type_created"
        ON "search_queries" ("search_type", "created_at");
    CREATE INDEX IF NOT EXISTS "idx_search_queries_user_created"
        ON "search_queries" ("user_profile_id", "created_at");

    -- Create embedding_models table
    CREATE TABLE IF NOT EXISTS "embedding_models" (
        "id" SERIAL NOT NULL PRIMARY KEY,
        "model_name" VARCHAR(200) NOT NULL UNIQUE,
        "model_version" VARCHAR(100) NOT NULL,
        "dimensions" INT NOT NULL,
        "max_tokens" INT NOT NULL,
        "language_support" JSONB NOT NULL DEFAULT '[]',
        "avg_embedding_time_ms" DOUBLE PRECISION,
        "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "embedding_models";
    DROP TABLE IF EXISTS "search_queries";
    DROP TABLE IF EXISTS "document_chunks";
    DROP TABLE IF EXISTS "pharmaceutical_documents";
    -- Note: We don't drop the vector extension as other tables might use it
    """
