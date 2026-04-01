from tortoise import fields, models


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
