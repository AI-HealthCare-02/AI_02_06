from tortoise import fields, models


class PushToken(models.Model):
    """
    푸시 알림 토큰 관리 모델
    - FCM 디바이스 토큰 저장
    - last_active_at으로 비활성 토큰 정리 (네트워크 비용 절감)
    - device_token UNIQUE 제약으로 중복 등록 방지
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["models.Model"] = fields.ForeignKeyField(
        "models.User",
        related_name="push_tokens",
        on_delete=fields.CASCADE,
        description="토큰 소유자",
    )
    device_token = fields.CharField(
        max_length=256,
        unique=True,
        description="FCM 디바이스 토큰",
    )
    device_info = fields.CharField(
        max_length=256,
        null=True,
        description="기기 정보 (OS, 모델 등)",
    )
    last_active_at = fields.DatetimeField(
        null=True,
        description="마지막 활성 일시 (비활성 토큰 정리용)",
        db_index=True,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "push_tokens"

    def __str__(self) -> str:
        return f"PushToken(user_id={self.user_id}, token={self.device_token[:20]}...)"
