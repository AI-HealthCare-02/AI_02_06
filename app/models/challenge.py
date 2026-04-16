"""Challenge model module.

This module defines the Challenge model for storing user challenge information
including progress tracking and completion status.
"""

from tortoise import fields, models


class Challenge(models.Model):
    """Challenge model for tracking user health challenges.

    This model stores challenge information including title, description,
    target days, completion tracking, and status.

    Attributes:
        id: Primary key UUID.
        profile: Foreign key to Profile model.
        title: Challenge title (max 64 characters).
        description: Optional detailed description (max 256 characters).
        target_days: Target number of days to complete.
        completed_dates: JSON array of completion dates.
        challenge_status: Current status (default: IN_PROGRESS).
        started_date: Challenge start date.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
        deleted_at: Soft deletion timestamp.
    """

    id = fields.UUIDField(pk=True)
    profile = fields.ForeignKeyField("models.Profile", related_name="challenges")

    title = fields.CharField(max_length=64, description="Challenge title")
    description = fields.CharField(max_length=256, null=True, description="Detailed description")
    target_days = fields.IntField(description="Target completion days")

    # Store completion dates as JSON array instead of separate ChallengeLog table
    completed_dates = fields.JSONField(default=list, description="List of completion dates")

    challenge_status = fields.CharField(max_length=16, default="IN_PROGRESS", description="Progress status")
    started_date = fields.DateField(description="Challenge start date")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "challenges"
        indexes = (("profile_id", "challenge_status"),)
