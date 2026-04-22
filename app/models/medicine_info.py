"""MedicineInfo model for the pharmaceutical RAG knowledge base.

Stores one row per medicine with a pgvector embedding column used for
hybrid similarity search. Field shape mirrors `ai_worker/data/medicines.json`.
"""

from tortoise import fields, models

from app.db.vector_field import VectorField
from app.services.rag.config import EMBEDDING_DIMENSIONS


class MedicineInfo(models.Model):
    """Medicine knowledge base entry with vector embedding for RAG retrieval."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=128, unique=True, description="약품명")
    ingredient = fields.TextField(description="주성분")
    usage = fields.CharField(max_length=64, description="주된 용도")
    disclaimer = fields.TextField(description="복용 시 주의사항")
    contraindicated_drugs = fields.JSONField(default=list, description="병용 금기 약물 리스트")
    contraindicated_foods = fields.JSONField(default=list, description="병용 금기 음식 리스트")

    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, description="하이브리드 검색용 임베딩")
    embedding_normalized = fields.BooleanField(default=True, description="임베딩 L2 정규화 여부")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medicine_info"
        table_description = "RAG 검색을 위한 표준 약학 정보"
