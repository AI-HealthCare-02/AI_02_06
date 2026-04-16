"""Drug interaction cache model module.

This module defines the DrugInteractionCache model for caching DUR (Drug Utilization Review)
interaction results to reduce public API costs.

REQ-MED-004: Public API cost reduction through caching.
"""

from tortoise import fields, models


class DrugInteractionCache(models.Model):
    """Drug interaction cache model for DUR analysis results.

    This model caches DUR interaction analysis results to reduce public API costs.
    Uses drug_pair as a sorted combination of two drug names (e.g., "aspirin::tylenol").
    Implements TTL-based cache expiration management.

    Attributes:
        id: Primary key for cache record.
        drug_pair: Sorted drug pair key (e.g., "aspirin::tylenol").
        interaction: DUR interaction analysis results as JSON.
        expires_at: Cache expiration timestamp.
        created_at: Cache creation timestamp.
    """

    id = fields.BigIntField(
        primary_key=True,
        description="Cache record ID",
    )
    drug_pair = fields.CharField(
        max_length=256,
        unique=True,
        description="Sorted drug pair key (e.g., aspirin::tylenol)",
        db_index=True,
    )
    interaction = fields.JSONField(
        description="DUR interaction analysis results",
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
        table = "drug_interaction_cache"

    def __str__(self) -> str:
        return f"DrugInteractionCache({self.drug_pair})"
