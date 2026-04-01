from tortoise import fields, models


class MessageFeedback(models.Model):
    id = fields.UUIDField(pk=True)
    message = fields.OneToOneField("models.ChatMessage", related_name="feedback")
    is_helpful = fields.BooleanField()
    feedback_text = fields.CharField(max_length=256, null=True)
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "message_feedbacks"
