from tortoise import fields, models


class RefreshToken(models.Model):
    """
    Refresh Token 관리 모델
    - REQ-USR-AUT-010: 토큰 기반 인증 보안 강화
    - 토큰 해시값 저장으로 원본 노출 방지
    - is_revoked 플래그로 즉시 무효화 지원
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["models.Model"] = fields.ForeignKeyField(
        "models.User",
        related_name="refresh_tokens",
        on_delete=fields.CASCADE,
        description="토큰 소유자",
    )
    token_hash = fields.CharField(
        max_length=64,
        description="SHA-256 해시값 (원본 토큰 미저장)",
        db_index=True,
    )
    is_revoked = fields.BooleanField(
        default=False,
        description="무효화 여부 (로그아웃/강제만료 시 True)",
    )
    expires_at = fields.DatetimeField(
        description="토큰 만료 일시",
    )
    device_info = fields.CharField(
        max_length=256,
        null=True,
        description="User-Agent 또는 기기 식별 정보",
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "refresh_tokens"
        indexes = [
            ("user_id", "is_revoked"),
        ]

    def __str__(self) -> str:
        return f"RefreshToken(user_id={self.user_id}, revoked={self.is_revoked})"
