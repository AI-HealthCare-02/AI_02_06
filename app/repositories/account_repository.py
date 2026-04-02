"""
Account Repository

accounts 테이블 데이터 접근 계층
"""

from uuid import UUID, uuid4

from app.models.accounts import Account, AuthProvider


class AccountRepository:
    """Account DB 저장소"""

    async def get_by_provider(self, provider: AuthProvider, provider_account_id: str) -> Account | None:
        """소셜 로그인 정보로 계정 조회"""
        return await Account.filter(
            auth_provider=provider,
            provider_account_id=provider_account_id,
            deleted_at__isnull=True,
        ).first()

    async def get_by_id(self, account_id: UUID) -> Account | None:
        """계정 ID로 조회"""
        return await Account.filter(
            id=account_id,
            deleted_at__isnull=True,
        ).first()

    async def create(
        self,
        provider: AuthProvider,
        provider_account_id: str,
        email: str | None,
        nickname: str,
    ) -> Account:
        """새 계정 생성"""
        return await Account.create(
            id=uuid4(),
            auth_provider=provider,
            provider_account_id=provider_account_id,
            email=email,
            nickname=nickname,
            is_active=True,
        )

    async def update_login_info(
        self,
        account: Account,
        email: str | None,
        nickname: str,
    ) -> Account:
        """로그인 시 최신 정보로 업데이트"""
        account.email = email
        account.nickname = nickname
        await account.save()
        return account

    async def deactivate(self, account: Account) -> Account:
        """계정 비활성화"""
        account.is_active = False
        await account.save()
        return account
