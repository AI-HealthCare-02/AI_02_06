"""
Refresh Token Repository

DB에 refresh token을 저장/조회/무효화합니다.
토큰 원본이 아닌 SHA-256 해시값만 저장합니다.
RTR (Refresh Token Rotation) + Grace Period 지원
"""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from tortoise.expressions import Q

from app.core import config
from app.models.refresh_tokens import RefreshToken

# Grace Period: 동시 요청 대응 (RTR 후에도 구 토큰 일시 유효)
GRACE_PERIOD_SECONDS = 2


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

    async def validate_with_grace(self, token: str) -> tuple[RefreshToken | None, bool]:
        """
        Grace Period를 고려한 토큰 검증

        Returns:
            tuple[RefreshToken | None, bool]: (토큰 객체, 유효 여부)
            - (token, True): 유효한 토큰
            - (token, True): RTR되었지만 Grace Period 내 (유효)
            - (token, False): Grace Period 초과 (탈취 의심)
            - (None, False): 토큰 없음
        """
        token_hash = self._hash_token(token)
        now = datetime.now()

        # 1. 해시로 토큰 조회 (revoked 여부 무관)
        refresh_token = await RefreshToken.filter(token_hash=token_hash).first()

        if not refresh_token:
            return None, False

        # 2. 만료 확인
        if refresh_token.expires_at < now:
            return refresh_token, False

        # 3. 아직 revoke 안 된 토큰 → 유효
        if not refresh_token.is_revoked:
            return refresh_token, True

        # 4. Revoked 토큰 → Grace Period 확인
        if refresh_token.rotated_at:
            grace_deadline = refresh_token.rotated_at + timedelta(seconds=GRACE_PERIOD_SECONDS)
            if now <= grace_deadline:
                # Grace Period 내 → 유효 (동시 요청 허용)
                return refresh_token, True

        # 5. Grace Period 초과 → 탈취 의심
        return refresh_token, False

    async def rotate(self, old_token: str, account_id: UUID, new_token: str) -> tuple[RefreshToken | None, bool]:
        """
        토큰 교체 (RTR) - 낙관적 잠금으로 Race Condition 방지

        1. 기존 토큰이 아직 revoke 안 된 경우에만 무효화
        2. 새 토큰 생성
        3. 기존 토큰에 replaced_by_id 기록

        Returns:
            tuple[RefreshToken | None, bool]: (새 토큰, 성공 여부)
            - (new_token, True): 정상 교체
            - (None, False): 이미 다른 요청에서 교체됨 (Race Condition)
        """
        old_token_hash = self._hash_token(old_token)
        now = datetime.now()

        # 1. 낙관적 잠금: is_revoked=False인 경우에만 업데이트
        updated = await RefreshToken.filter(
            token_hash=old_token_hash,
            is_revoked=False,  # 아직 revoke 안 된 토큰만
        ).update(
            is_revoked=True,
            rotated_at=now,
        )

        # 이미 다른 요청에서 교체된 경우
        if updated == 0:
            return None, False

        # 2. 새 토큰 생성
        new_refresh_token = await self.create(account_id, new_token)

        # 3. replaced_by_id 업데이트 (추적용)
        await RefreshToken.filter(token_hash=old_token_hash).update(
            replaced_by_id=new_refresh_token.id,
        )

        return new_refresh_token, True

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

    async def cleanup_expired_tokens(self, days_old: int = 7) -> int:
        """
        만료된 토큰 정리 (DB 비대화 방지)

        - expires_at이 지난 토큰 삭제
        - days_old일 이상 지난 revoked 토큰 삭제
        - 주기적으로 실행 권장 (cron job 또는 스케줄러)

        Returns:
            삭제된 토큰 수
        """
        cutoff = datetime.now() - timedelta(days=days_old)

        # 조건: 만료된 토큰 OR (revoked이고 rotated_at이 오래된 토큰)
        deleted = await RefreshToken.filter(
            Q(expires_at__lt=cutoff) | Q(is_revoked=True, rotated_at__lt=cutoff)
        ).delete()

        return deleted
