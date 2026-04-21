"""Medicine information model module.

This module defines the MedicineInfo model for the pharmaceutical
knowledge base, integrating public API data and supporting RAG search.
"""

from tortoise import fields, models


class MedicineInfo(models.Model):
    """Pharmaceutical knowledge base for RAG search and public API data.

    Stores drug permit data from the Food and Drug Safety public API
    (getDrugPrdtPrmsnDtlInq06) and supports vector similarity search
    via pgvector for the RAG pipeline.

    Attributes:
        id: Auto-increment primary key.
        item_seq: Unique drug product code from public API (UPSERT key).
        medicine_name: Drug product name in Korean.
        item_eng_name: Drug product name in English.
        entp_name: Manufacturer name.
        product_type: Product classification code.
        spclty_pblc: Professional/OTC drug classification.
        permit_date: Permit date in YYYYMMDD format.
        cancel_name: Current status (normal/cancelled).
        main_item_ingr: Active ingredients with standard codes.
        storage_method: Storage instructions.
        edi_code: Insurance billing codes.
        bizrno: Business registration number.
        change_date: Last change date from API in YYYYMMDD format.
        category: Drug category for search filtering.
        efficacy: Drug efficacy and effects.
        side_effects: Known side effects.
        precautions: Usage precautions.
        embedding: Vector embedding for similarity search.
        last_synced_at: Last sync timestamp from public API.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    id = fields.IntField(pk=True)

    # ── 공공데이터 API 필드 (getDrugPrdtPrmsnDtlInq06에서 수집) ──────────
    # item_seq를 UPSERT 기준 키로 사용하여 증분 업데이트 시 중복 방지
    item_seq = fields.CharField(
        max_length=20,
        unique=True,
        null=True,
        description="Drug product code from public API (UPSERT key)",
    )
    medicine_name = fields.CharField(
        max_length=200,
        unique=True,
        description="Drug product name in Korean",
    )
    item_eng_name = fields.CharField(
        max_length=256,
        null=True,
        description="Drug product name in English",
    )
    entp_name = fields.CharField(
        max_length=128,
        null=True,
        description="Manufacturer name",
    )
    product_type = fields.CharField(
        max_length=64,
        null=True,
        description="Product classification code",
    )
    spclty_pblc = fields.CharField(
        max_length=32,
        null=True,
        description="Professional or OTC drug classification",
    )
    permit_date = fields.CharField(
        max_length=8,
        null=True,
        description="Permit date in YYYYMMDD format",
    )
    cancel_name = fields.CharField(
        max_length=16,
        null=True,
        description="Current status (normal or cancelled)",
    )
    main_item_ingr = fields.TextField(
        null=True,
        description="Active ingredients with standard codes",
    )
    storage_method = fields.TextField(
        null=True,
        description="Storage method and instructions",
    )
    edi_code = fields.CharField(
        max_length=256,
        null=True,
        description="Insurance billing codes (comma-separated)",
    )
    bizrno = fields.CharField(
        max_length=16,
        null=True,
        description="Business registration number",
    )
    change_date = fields.CharField(
        max_length=8,
        null=True,
        description="Last change date from API in YYYYMMDD format",
    )

    # ── RAG 지식 베이스 필드 (LLM 호출 또는 수동 큐레이션으로 채워짐) ───
    category = fields.CharField(
        max_length=64,
        null=True,
        description="Drug category for search filtering",
    )
    efficacy = fields.TextField(
        null=True,
        description="Drug efficacy and effects",
    )
    side_effects = fields.TextField(
        null=True,
        description="Known side effects",
    )
    precautions = fields.TextField(
        null=True,
        description="Usage precautions",
    )

    # ── 벡터 검색용 임베딩 (pgvector 확장으로 실제 벡터 연산 수행) ──────
    embedding = fields.TextField(
        null=True,
        description="OpenAI text embedding data for vector similarity search",
    )

    # ── 동기화 추적 및 타임스탬프 ──────────────────────────────────────
    last_synced_at = fields.DatetimeField(
        null=True,
        description="Last synchronization timestamp from public API",
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medicine_info"
        table_description = "Pharmaceutical knowledge base for RAG search and public API data"
