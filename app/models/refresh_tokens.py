"""
Refresh Token 모델

REQ-USR-AUT-010: 토큰 기반 인증 보안 강화
"""

from tortoise import fields, models


class RefreshToken(models.Model):
    """
    Refresh Token 관리 모델

    - 토큰 원본이 아닌 SHA-256 해시값만 저장 (보안)
    - 로그아웃 시 is_revoked = True로 즉시 무효화
    - 다중 기기 로그인 지원 (계정당 여러 토큰 가능)
    """

    id = fields.BigIntField(
        primary_key=True,
        description="토큰 레코드 ID",
    )
    account: fields.ForeignKeyRelation["models.Model"] = fields.ForeignKeyField(
        "models.Account",
        related_name="refresh_tokens",
        on_delete=fields.CASCADE,
        description="토큰 소유 계정",
    )
    token_hash = fields.CharField(
        max_length=64,
        description="Refresh Token SHA-256 해시값",
        db_index=True,
    )
    expires_at = fields.DatetimeField(
        description="토큰 만료 일시",
    )
    is_revoked = fields.BooleanField(
        default=False,
        description="토큰 무효화 여부 (로그아웃 시 True)",
    )
    created_at = fields.DatetimeField(
        auto_now_add=True,
        description="토큰 발급 일시",
    )

    class Meta:
        table = "refresh_tokens"
        indexes = [
            ("account_id", "is_revoked"),
        ]

    def __str__(self) -> str:
        return f"RefreshToken(account_id={self.account_id}, revoked={self.is_revoked})"
