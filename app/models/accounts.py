from enum import StrEnum

from tortoise import fields, models

"""
Account 모델 (뼈대)

TODO: 담당 팀원이 구현 예정
- 소셜 로그인 인증 정보 저장
- profiles, chat_sessions, refresh_tokens와 1:N 관계
"""


class AuthProvider(StrEnum):
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class Account(models.Model):
    id = fields.UUIDField(primary_key=True)
    auth_provider = fields.CharEnumField(enum_type=AuthProvider, max_length=16)
    provider_account_id = fields.CharField(max_length=128)
    nickname = fields.CharField(max_length=32)
    profile_image_url = fields.CharField(max_length=512, null=True)
    is_active = fields.BooleanField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "accounts"
