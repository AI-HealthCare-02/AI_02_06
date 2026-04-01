from enum import StrEnum

from tortoise import fields, models


class SenderType(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatSession(models.Model):
    id = fields.UUIDField(pk=True)
    account = fields.ForeignKeyField("models.Account", related_name="chat_sessions")
    profile = fields.ForeignKeyField("models.Profile", related_name="chat_sessions")
    medication = fields.ForeignKeyField("models.Medication", related_name="chat_sessions", null=True)
    title = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "chat_sessions"
        indexes = [
            ("account_id", "created_at"),
            ("profile_id",),
            ("medication_id",),
        ]


class ChatMessage(models.Model):
    id = fields.UUIDField(pk=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages")
    sender_type = fields.CharEnumField(enum_type=SenderType, max_length=16)
    content = fields.TextField()
    is_helpful = fields.BooleanField(null=True)
    feedback_text = fields.CharField(max_length=256, null=True)
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "messages"
        indexes = [
            ("session_id", "created_at"),
        ]
