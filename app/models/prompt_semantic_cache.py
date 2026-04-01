from tortoise import fields, models


class PromptSemanticCache(models.Model):
    """
    LLM 프롬프트 시맨틱 캐시 모델
    - LLM API 토큰 비용 절감 목적
    - prompt_hash (SHA-256)를 PK로 사용하여 중복 방지
    - hit_count로 캐시 효율성 측정
    """

    prompt_hash = fields.CharField(
        max_length=64,
        primary_key=True,
        description="프롬프트 SHA-256 해시값",
    )
    original_prompt = fields.TextField(
        description="원본 질문 텍스트",
    )
    query_category = fields.CharField(
        max_length=32,
        description="질문 카테고리 (GENERAL, MEDICAL 등)",
        db_index=True,
    )
    extracted_entities = fields.JSONField(
        null=True,
        description="추출된 고유명사/엔티티 (JSONB)",
    )
    response = fields.JSONField(
        description="캐시된 LLM 응답 (JSONB)",
    )
    hit_count = fields.IntField(
        default=0,
        description="캐시 히트 횟수",
    )
    last_accessed_at = fields.DatetimeField(
        null=True,
        description="마지막 조회 일시",
        db_index=True,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "prompt_semantic_cache"

    def __str__(self) -> str:
        return f"PromptSemanticCache(hash={self.prompt_hash[:16]}..., hits={self.hit_count})"
