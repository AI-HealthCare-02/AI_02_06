"""Vector Database Models for RAG System.

Models for storing pharmaceutical documents, chunks, and embeddings.
"""

from enum import StrEnum

from tortoise import fields
from tortoise.models import Model

from app.db.vector_field import VectorField, VectorQueryMixin


class DocumentType(StrEnum):
    """Document type enumeration."""

    PRESCRIPTION = "PRESCRIPTION"  # 처방전
    MEDICINE_INFO = "MEDICINE_INFO"  # 약품 정보
    DRUG_INTERACTION = "DRUG_INTERACTION"  # 약물 상호작용
    SIDE_EFFECT = "SIDE_EFFECT"  # 부작용 정보
    DOSAGE_GUIDE = "DOSAGE_GUIDE"  # 복용법 가이드
    CONTRAINDICATION = "CONTRAINDICATION"  # 금기사항


class ChunkType(StrEnum):
    """Chunk type based on pharmaceutical document sections."""

    EFFICACY = "EFFICACY"  # 효능, 효과
    DOSAGE = "DOSAGE"  # 용법, 용량
    PRECAUTION = "PRECAUTION"  # 사용상 주의사항
    INTERACTION = "INTERACTION"  # 약물 상호작용
    SIDE_EFFECT = "SIDE_EFFECT"  # 부작용
    CONTRAINDICATION = "CONTRAINDICATION"  # 금기사항
    STORAGE = "STORAGE"  # 보관법
    GENERAL = "GENERAL"  # 일반 정보


class UserCondition(StrEnum):
    """User condition for metadata filtering."""

    PREGNANT = "PREGNANT"  # 임부
    ELDERLY = "ELDERLY"  # 노인
    CHILD = "CHILD"  # 소아
    LACTATING = "LACTATING"  # 수유부
    DIABETIC = "DIABETIC"  # 당뇨병
    HYPERTENSIVE = "HYPERTENSIVE"  # 고혈압
    KIDNEY_DISEASE = "KIDNEY_DISEASE"  # 신장질환
    LIVER_DISEASE = "LIVER_DISEASE"  # 간질환


class PharmaceuticalDocument(Model, VectorQueryMixin):
    """Main document model for pharmaceutical information.

    Stores complete documents before chunking.
    """

    id = fields.IntField(pk=True)

    # Document identification
    title = fields.CharField(max_length=500, description="Document title")
    document_type = fields.CharEnumField(DocumentType, description="Type of document")
    source_url = fields.TextField(null=True, description="Original source URL")

    # Content
    content = fields.TextField(description="Full document content")
    content_hash = fields.CharField(max_length=64, unique=True, description="SHA256 hash of content")

    # Metadata for filtering
    medicine_names = fields.JSONField(default=list, description="List of medicine names in document")
    target_conditions = fields.JSONField(default=list, description="Target user conditions")
    language = fields.CharField(max_length=10, default="ko", description="Document language")

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_indexed_at = fields.DatetimeField(null=True, description="Last time document was indexed")

    # Document embedding (for document-level similarity)
    document_embedding = VectorField(dimensions=768, null=True, description="Document-level embedding")

    class Meta:
        table = "pharmaceutical_documents"
        indexes = [
            ("document_type", "created_at"),
            ("medicine_names",),  # GIN index for JSON array
            ("target_conditions",),  # GIN index for JSON array
        ]


class DocumentChunk(Model, VectorQueryMixin):
    """Chunked document model for fine-grained RAG retrieval.

    Stores document chunks with embeddings for similarity search.
    """

    id = fields.IntField(pk=True)

    # Relationship to parent document
    document = fields.ForeignKeyField(
        "models.PharmaceuticalDocument", related_name="chunks", on_delete=fields.CASCADE, description="Parent document"
    )

    # Chunk identification
    chunk_index = fields.IntField(description="Order of chunk in document")
    chunk_type = fields.CharEnumField(ChunkType, description="Type of chunk content")

    # Content
    content = fields.TextField(description="Chunk content")
    content_hash = fields.CharField(max_length=64, description="SHA256 hash of chunk content")

    # Chunk metadata
    section_title = fields.CharField(max_length=200, null=True, description="Section title if available")
    word_count = fields.IntField(description="Number of words in chunk")
    char_count = fields.IntField(description="Number of characters in chunk")

    # Metadata for hybrid search
    keywords = fields.JSONField(default=list, description="Extracted keywords for keyword search")
    medicine_names = fields.JSONField(default=list, description="Medicine names mentioned in chunk")
    dosage_info = fields.JSONField(default=dict, description="Dosage information if applicable")

    # User condition targeting
    target_conditions = fields.JSONField(default=list, description="Applicable user conditions")
    contraindicated_conditions = fields.JSONField(default=list, description="Contraindicated conditions")

    # Vector embedding
    embedding = VectorField(dimensions=768, description="Chunk embedding for similarity search")

    # Search optimization
    embedding_normalized = fields.BooleanField(default=False, description="Whether embedding is normalized")

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "document_chunks"
        unique_together = [("document", "chunk_index")]
        indexes = [
            ("chunk_type", "created_at"),
            ("medicine_names",),  # GIN index for JSON array
            ("keywords",),  # GIN index for JSON array
            ("target_conditions",),  # GIN index for JSON array
            ("embedding",),  # HNSW index for vector similarity (created via migration)
        ]


class SearchQuery(Model):
    """Model to store search queries for analytics and optimization."""

    id = fields.IntField(pk=True)

    # Query information
    query_text = fields.TextField(description="Original query text")
    query_embedding = VectorField(dimensions=768, null=True, description="Query embedding")

    # Search parameters
    search_type = fields.CharField(max_length=50, description="Type of search performed")
    filters_applied = fields.JSONField(default=dict, description="Filters applied to search")

    # Results
    results_count = fields.IntField(description="Number of results returned")
    top_chunk_ids = fields.JSONField(default=list, description="IDs of top retrieved chunks")

    # Performance metrics
    search_duration_ms = fields.IntField(description="Search duration in milliseconds")

    # User context (optional, for personalization)
    user_profile_id = fields.IntField(null=True, description="User profile ID if available")
    user_conditions = fields.JSONField(default=list, description="User conditions at search time")

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "search_queries"
        indexes = [
            ("created_at",),
            ("search_type", "created_at"),
            ("user_profile_id", "created_at"),
        ]


class EmbeddingModel(Model):
    """Model to track embedding models and their configurations."""

    id = fields.IntField(pk=True)

    # Model information
    model_name = fields.CharField(max_length=200, unique=True, description="Embedding model name")
    model_version = fields.CharField(max_length=100, description="Model version")
    dimensions = fields.IntField(description="Embedding dimensions")

    # Configuration
    max_tokens = fields.IntField(description="Maximum tokens per input")
    language_support = fields.JSONField(default=list, description="Supported languages")

    # Performance metrics
    avg_embedding_time_ms = fields.FloatField(null=True, description="Average embedding time")

    # Status
    is_active = fields.BooleanField(default=True, description="Whether model is currently active")

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "embedding_models"
