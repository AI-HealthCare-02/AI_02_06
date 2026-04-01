"""
Account 모델 (뼈대)

TODO: 담당 팀원이 구현 예정
- 소셜 로그인 인증 정보 저장
- profiles, chat_sessions, refresh_tokens와 1:N 관계
"""

from tortoise import fields, models


class Account(models.Model):
    """로그인 계정 - 담당 팀원 구현 예정"""

    id = fields.UUIDField(primary_key=True)
    # TODO: auth_provider, provider_account_id, email, nickname, is_active 등

    class Meta:
        table = "accounts"
