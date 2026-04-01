"""
LLM 응답 캐시 모델

비용 최적화: LLM API 토큰 비용 절감
"""

from tortoise import fields, models


class LLMResponseCache(models.Model):
    """
    LLM 응답 캐시 모델

    - 동일/유사 질문에 대한 토큰 비용 절감
    - 프롬프트 SHA-256 해시 기반 시맨틱 캐싱
    - hit_count로 캐시 효율 모니터링
    """

    id = fields.BigIntField(
        primary_key=True,
        description="캐시 레코드 ID",
    )
    prompt_hash = fields.CharField(
        max_length=64,
        unique=True,
        description="프롬프트 SHA-256 해시값",
        db_index=True,
    )
    prompt_text = fields.TextField(
        description="원본 프롬프트 텍스트",
    )
    response = fields.JSONField(
        description="LLM 응답 데이터",
    )
    hit_count = fields.IntField(
        default=0,
        description="캐시 히트 횟수",
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
        table = "llm_response_cache"

    def __str__(self) -> str:
        return f"LLMResponseCache(hash={self.prompt_hash[:16]}..., hits={self.hit_count})"
