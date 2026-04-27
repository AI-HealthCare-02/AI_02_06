"""Medication model module.

This module defines the Medication model for storing prescription medication
information and intake schedules.
"""

from tortoise import fields, models


class Medication(models.Model):
    """Medication model for prescription tracking.

    This model stores prescription medication information including dosage,
    intake schedules, and prescription details.

    Attributes:
        id: Primary key UUID.
        profile: Foreign key to Profile model.
        medicine_name: Name of the medication.
        dose_per_intake: Dosage per intake (e.g., "1 tablet", "5ml").
        intake_instruction: Intake instructions.
        intake_times: Daily intake times as JSON array.
        total_intake_count: Total prescribed intake count.
        remaining_intake_count: Remaining intake count.
        start_date: Medication start date.
        end_date: Expected end date.
        dispensed_date: Medication dispensing date.
        expiration_date: Medication expiration date.
        is_active: Whether currently taking medication.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
        deleted_at: Soft deletion timestamp.
    """

    id = fields.UUIDField(pk=True)

    # Connected to profiles table
    profile = fields.ForeignKeyField("models.Profile", related_name="medications")

    medicine_name = fields.CharField(max_length=128, description="약품명")
    department = fields.CharField(max_length=64, null=True, description="처방 진료과 (예: 내과)")
    category = fields.CharField(max_length=64, null=True, description="약품 분류 (예: 해열진통제)")
    dose_per_intake = fields.CharField(max_length=32, null=True, description="1회 복용량 (예: 1정, 5ml)")
    daily_intake_count = fields.IntField(null=True, description="1일 복용 횟수")
    total_intake_days = fields.IntField(null=True, description="총 복용 일수")
    intake_instruction = fields.CharField(max_length=256, null=True, description="복용 지시사항")

    # Use PostgreSQL JSONB to store arrays like ["08:00", "13:00"]
    intake_times = fields.JSONField(description="Daily intake times list")

    total_intake_count = fields.IntField(description="Total prescribed intake count")
    remaining_intake_count = fields.IntField(description="Remaining intake count")

    start_date = fields.DateField(description="Medication start date")
    end_date = fields.DateField(null=True, description="Expected end date")
    dispensed_date = fields.DateField(null=True, description="Medication dispensing date")
    expiration_date = fields.DateField(null=True, description="Medication expiration date")

    is_active = fields.BooleanField(default=True, description="Currently taking medication")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "medications"
        indexes = (("profile_id", "is_active"),)
