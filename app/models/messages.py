from enum import StrEnum

from tortoise import fields, models


class SenderType(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatMessage(models.Model):
    id = fields.UUIDField(pk=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages")
    sender_type = fields.CharEnumField(enum_type=SenderType, max_length=16)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "messages"
        indexes = [
            ("session_id", "created_at"),
        ]
