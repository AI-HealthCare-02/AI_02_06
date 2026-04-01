"""
DUR 병용금기 캐시 모델

REQ-MED-004: 공공 API 호출 비용 절감
"""

from tortoise import fields, models


class DrugInteractionCache(models.Model):
    """
    DUR 병용금기 캐시 모델

    - 공공 API 호출 비용 절감 목적
    - drug_pair: 두 약품명을 정렬하여 결합 (예: "아스피린::타이레놀")
    - TTL 기반 캐시 만료 관리
    """

    id = fields.BigIntField(
        primary_key=True,
        description="캐시 레코드 ID",
    )
    drug_pair = fields.CharField(
        max_length=256,
        unique=True,
        description="정렬된 약품쌍 키 (예: 아스피린::타이레놀)",
        db_index=True,
    )
    interaction = fields.JSONField(
        description="DUR 상호작용 분석 결과",
    )
    expires_at = fields.DatetimeField(
        description="캐시 만료 일시",
        db_index=True,
    )
    created_at = fields.DatetimeField(
        auto_now_add=True,
        description="캐시 생성 일시",
    )

    class Meta:
        table = "drug_interaction_cache"

    def __str__(self) -> str:
        return f"DrugInteractionCache({self.drug_pair})"
