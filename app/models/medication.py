from tortoise import fields, models


class Medication(models.Model):
    id = fields.UUIDField(pk=True)

    # profiles 테이블과 연결
    profile = fields.ForeignKeyField('models.Profile', related_name='medications')

    medicine_name = fields.CharField(max_length=128, description="약품명")
    dose_per_intake = fields.CharField(max_length=32, null=True, description="1회 복용량 (예: 1정, 5ml)")
    intake_instruction = fields.CharField(max_length=256, null=True, description="복용 지시사항")

    # PostgreSQL의 JSONB를 활용하여 ["08:00", "13:00"] 같은 배열을 통째로 저장합니다.
    intake_times = fields.JSONField(description="일일 복용 시간 목록")

    total_intake_count = fields.IntField(description="처방된 총 복용 횟수")
    remaining_intake_count = fields.IntField(description="남은 복용 횟수")

    start_date = fields.DateField(description="복용 시작일")
    end_date = fields.DateField(null=True, description="복용 종료 예정일")
    dispensed_date = fields.DateField(null=True, description="약품 조제일")
    expiration_date = fields.DateField(null=True, description="약품 유효기간 만료일")
    prescription_image_url = fields.CharField(max_length=512, null=True, description="처방전 이미지 URL")

    is_active = fields.BooleanField(default=True, description="현재 복용 중 여부")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "medications"
        indexes = (
            ("profile_id", "is_active"),
        )
