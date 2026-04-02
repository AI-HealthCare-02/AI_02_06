"""
Refresh Token Repository

DB에 refresh token을 저장/조회/무효화합니다.
토큰 원본이 아닌 SHA-256 해시값만 저장합니다.
"""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from app.core import config
from app.models.refresh_tokens import RefreshToken


class RefreshTokenRepository:
    """Refresh Token DB 저장소"""

    @staticmethod
    def _hash_token(token: str) -> str:
        """토큰을 SHA-256 해시로 변환"""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, account_id: UUID, token: str) -> RefreshToken:
        """새 refresh token 저장"""
        token_hash = self._hash_token(token)
        expires_at = datetime.now() + timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)

        return await RefreshToken.create(
            account_id=account_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """토큰으로 조회 (유효한 토큰만)"""
        token_hash = self._hash_token(token)
        return await RefreshToken.filter(
            token_hash=token_hash,
            is_revoked=False,
            expires_at__gt=datetime.now(),
        ).first()

    async def revoke(self, token: str) -> bool:
        """토큰 무효화 (로그아웃)"""
        token_hash = self._hash_token(token)
        updated = await RefreshToken.filter(
            token_hash=token_hash,
            is_revoked=False,
        ).update(is_revoked=True)
        return updated > 0

    async def revoke_all_for_account(self, account_id: UUID) -> int:
        """계정의 모든 토큰 무효화 (전체 로그아웃)"""
        updated = await RefreshToken.filter(
            account_id=account_id,
            is_revoked=False,
        ).update(is_revoked=True)
        return updated
