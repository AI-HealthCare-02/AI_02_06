from enum import StrEnum

from tortoise import fields, models


class RelationType(StrEnum):
    SELF = "SELF"
    PARENT = "PARENT"
    CHILD = "CHILD"
    SPOUSE = "SPOUSE"
    OTHER = "OTHER"


class Profile(models.Model):
    id = fields.UUIDField(primary_key=True)
    account_id = fields.ForeignKeyField("models.Account")
    relation_type = fields.CharEnumField(enum_type=RelationType)
    name = fields.CharField(max_length=32)
    health_survey = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "profiles"
