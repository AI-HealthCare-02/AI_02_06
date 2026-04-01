from tortoise import fields, models


class IntakeLog(models.Model):
    id = fields.UUIDField(pk=True)

    medication = fields.ForeignKeyField('models.Medication', related_name='intake_logs')
    # 조회 속도(Join 최소화)를 위해 프로필 ID를 여기에도 비정규화로 넣어줍니다.
    profile = fields.ForeignKeyField('models.Profile', related_name='intake_logs')

    scheduled_date = fields.DateField(description="복용 예정 날짜")
    scheduled_time = fields.TimeField(description="복용 예정 시간")

    # PENDING -> SCHEDULED로 기본 상태값이 변경되었습니다.
    intake_status = fields.CharField(max_length=16, default='SCHEDULED', description="복용 상태")
    taken_at = fields.DatetimeField(null=True, description="실제 복용 완료 시간")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 캐시/로그성 데이터라 deleted_at(소프트 딜리트)은 제외되었습니다.

    class Meta:
        table = "intake_logs"
        indexes = (
            ("profile_id", "scheduled_date"),
            ("scheduled_date", "intake_status"),
        )