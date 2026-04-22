"""Medicine chunk model module.

This module defines the MedicineChunk model storing section-level
text chunks and their dense vector embeddings (pgvector VECTOR(768),
using the `jhgan/ko-sroberta-multitask` sentence-transformer) for
RAG similarity search.

The actual `vector(768)` column type and the HNSW index are applied
via manual SQL inside the Aerich migration because Tortoise ORM does
not natively understand the pgvector extension type.
"""

from enum import StrEnum

from tortoise import fields, models


class MedicineChunkSection(StrEnum):
    """RAG 청크 섹션 타입 (스키마 락: 13종 고정).

    공공데이터 API 의 EE_DOC / UD_DOC / NB_DOC ARTICLE 구조와
    medicine_info 메타 필드를 기반으로 고정된 분류 체계이다.
    팀원에게 공유되는 계약이므로 값 추가/변경 시 팀 공지 필수.
    """

    EFFICACY = "efficacy"
    USAGE = "usage"
    STORAGE = "storage"
    INGREDIENT = "ingredient"
    PRECAUTION_WARNING = "precaution_warning"
    PRECAUTION_CONTRAINDICATION = "precaution_contraindication"
    PRECAUTION_CAUTION = "precaution_caution"
    ADVERSE_REACTION = "adverse_reaction"
    PRECAUTION_GENERAL = "precaution_general"
    PRECAUTION_PREGNANCY = "precaution_pregnancy"
    PRECAUTION_PEDIATRIC = "precaution_pediatric"
    PRECAUTION_ELDERLY = "precaution_elderly"
    PRECAUTION_OVERDOSE = "precaution_overdose"


class MedicineChunk(models.Model):
    """Section-level embedding chunk for a medicine_info record.

    One medicine_info row yields multiple chunks (one per section, or
    several when an ARTICLE exceeds the model context window). The
    embedding column is materialised as `vector(768)` by a manual
    SQL migration step.

    Attributes:
        id: Auto-increment primary key.
        medicine_info: FK to parent drug (ON DELETE CASCADE).
        section: Chunk section tag (one of MedicineChunkSection).
        chunk_index: Sub-chunk order when an ARTICLE is split by token limit.
        content: Final embedding-target string with header prefix applied.
        token_count: Token count for monitoring and chunk-size tuning.
        embedding: pgvector(768) dense embedding (managed via raw SQL).
        model_version: Embedding model identifier for re-embedding tracking.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    # ── 기본 식별자 ────────────────────────────────────────────────────
    id = fields.BigIntField(pk=True)

    # ── 부모 약품 참조 (ON DELETE CASCADE) ────────────────────────────
    # medicine_info 삭제 시 연결된 청크도 전부 제거되어야 함
    medicine_info = fields.ForeignKeyField(
        "models.MedicineInfo",
        related_name="chunks",
        on_delete=fields.CASCADE,
        description="Parent medicine_info reference",
    )

    # ── 섹션 분류 및 분할 순번 ─────────────────────────────────────────
    # section: ARTICLE title 기반 섹션 enum (스키마 락)
    # chunk_index: ARTICLE이 128토큰 초과로 분할될 때 순번 (기본 0)
    section = fields.CharField(
        max_length=48,
        description="Chunk section tag (MedicineChunkSection)",
    )
    chunk_index = fields.IntField(
        default=0,
        description="Sub-chunk order when ARTICLE is split by token limit",
    )

    # ── 청크 본문 및 임베딩 ────────────────────────────────────────────
    # content: 헤더 프리픽스 포함 최종 임베딩 대상 텍스트
    # embedding: 실제 타입은 vector(768), Aerich 수동 SQL로 적용
    content = fields.TextField(
        description="Final embedding-target text with header prefix",
    )
    token_count = fields.IntField(
        null=True,
        description="Token count for monitoring",
    )
    embedding = fields.TextField(
        null=True,
        description="pgvector VECTOR(768) - materialised via manual SQL",
    )

    # ── 재임베딩 추적용 모델 버전 ──────────────────────────────────────
    # model 교체/업그레이드 시 부분 재임베딩의 기준이 되는 컬럼
    model_version = fields.CharField(
        max_length=64,
        description="Embedding model version (e.g. ko-sroberta-multitask-v1)",
    )

    # ── 타임스탬프 ─────────────────────────────────────────────────────
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medicine_chunk"
        table_description = "Section-level embedding chunks for RAG similarity search"
        unique_together = (("medicine_info", "section", "chunk_index"),)
        indexes = (
            ("medicine_info_id",),
            ("section",),
            ("model_version",),
        )
