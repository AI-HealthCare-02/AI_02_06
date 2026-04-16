"""LLM response cache model module.

This module defines the LLMResponseCache model for caching LLM API responses
to reduce token costs through semantic caching.

Cost optimization: Reduces LLM API token costs through response caching.
"""

from tortoise import fields, models


class LLMResponseCache(models.Model):
    """LLM response cache model for token cost optimization.

    This model caches LLM responses for identical/similar questions to reduce token costs.
    Uses SHA-256 hash-based semantic caching with hit count monitoring for cache efficiency.

    Attributes:
        id: Primary key for cache record.
        prompt_hash: SHA-256 hash of the prompt.
        prompt_text: Original prompt text.
        response: LLM response data as JSON.
        hit_count: Cache hit counter for efficiency monitoring.
        expires_at: Cache expiration timestamp.
        created_at: Cache creation timestamp.
    """

    id = fields.BigIntField(
        primary_key=True,
        description="Cache record ID",
    )
    prompt_hash = fields.CharField(
        max_length=64,
        unique=True,
        description="SHA-256 hash of prompt",
        db_index=True,
    )
    prompt_text = fields.TextField(
        description="Original prompt text",
    )
    response = fields.JSONField(
        description="LLM response data",
    )
    hit_count = fields.IntField(
        default=0,
        description="Cache hit count",
    )
    expires_at = fields.DatetimeField(
        description="Cache expiration timestamp",
        db_index=True,
    )
    created_at = fields.DatetimeField(
        auto_now_add=True,
        description="Cache creation timestamp",
    )

    class Meta:
        table = "llm_response_cache"

    def __str__(self) -> str:
        return f"LLMResponseCache(hash={self.prompt_hash[:16]}..., hits={self.hit_count})"
