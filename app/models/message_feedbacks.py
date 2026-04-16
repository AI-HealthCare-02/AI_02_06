"""Message feedback model module.

This module defines the MessageFeedback model for storing user feedback
on AI assistant responses.
"""

from tortoise import fields, models


class MessageFeedback(models.Model):
    """Message feedback model for user response evaluation.

    This model stores user feedback on AI assistant messages to improve
    response quality and user experience.

    Attributes:
        id: Primary key UUID.
        message: One-to-one relationship with ChatMessage.
        is_helpful: Whether the message was helpful.
        feedback_text: Optional detailed feedback text.
        metadata: Optional additional metadata as JSON.
        created_at: Feedback creation timestamp.
    """

    id = fields.UUIDField(pk=True)
    message = fields.OneToOneField("models.ChatMessage", related_name="feedback")
    is_helpful = fields.BooleanField()
    feedback_text = fields.CharField(max_length=256, null=True)
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "message_feedbacks"
