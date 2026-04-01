from tortoise import fields, models


class DrugInteractionCache(models.Model):
    """
    DUR 약물 상호작용 캐시 모델
    - 외부 공공 API 호출 비용 절감 목적
    - drug_a, drug_b 조합으로 캐시 히트 판단
    - expired_at 기준 TTL 관리
    """

    id = fields.BigIntField(primary_key=True)
    drug_a = fields.CharField(
        max_length=100,
        description="약품 A 명칭",
        db_index=True,
    )
    drug_b = fields.CharField(
        max_length=100,
        description="약품 B 명칭",
        db_index=True,
    )
    interaction_result = fields.JSONField(
        description="상호작용 분석 결과 (JSONB)",
    )
    expired_at = fields.DatetimeField(
        description="캐시 만료 일시 (TTL)",
        db_index=True,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "drug_interactions_cache"
        unique_together = [("drug_a", "drug_b")]

    def __str__(self) -> str:
        return f"DrugInteractionCache({self.drug_a} + {self.drug_b})"
