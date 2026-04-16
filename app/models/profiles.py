"""Profile model module.

This module defines the Profile model for storing user profile information
including family relationships and health survey data.
"""

from enum import StrEnum

from tortoise import fields, models


class RelationType(StrEnum):
    """Relationship type enumeration for family members."""

    SELF = "SELF"
    PARENT = "PARENT"
    CHILD = "CHILD"
    SPOUSE = "SPOUSE"
    OTHER = "OTHER"


class Profile(models.Model):
    """Profile model for storing user and family member information.

    This model stores profile information for users and their family members,
    including relationship types and health survey data.

    Attributes:
        id: Primary key UUID.
        account: Foreign key to Account model.
        relation_type: Relationship type (SELF, PARENT, CHILD, etc.).
        name: Profile name.
        health_survey: JSON field for health survey data.
        created_at: Profile creation timestamp.
        updated_at: Last update timestamp.
        deleted_at: Soft deletion timestamp.
    """

    id = fields.UUIDField(primary_key=True)
    account = fields.ForeignKeyField("models.Account", related_name="profiles")
    relation_type = fields.CharEnumField(enum_type=RelationType, max_length=16)
    name = fields.CharField(max_length=32)
    health_survey = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "profiles"
        indexes = (("account_id", "relation_type"),)
