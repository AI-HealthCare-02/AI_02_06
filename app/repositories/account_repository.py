"""
Account Repository (Mock 버전)

실제 DB 연동 전까지 메모리에 데이터를 저장합니다.
나중에 DB 연동 시 Tortoise ORM 버전으로 교체하면 됩니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.models.accounts import AuthProvider


@dataclass
class MockAccount:
    """Mock Account 데이터 클래스"""

    id: UUID
    auth_provider: str
    provider_account_id: str
    email: str | None
    nickname: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AccountRepository:
    """Account 메모리 저장소 (Mock)"""

    # 클래스 변수로 메모리 저장소 (서버 재시작 시 초기화됨)
    _storage: dict[UUID, MockAccount] = {}

    async def get_by_provider(self, provider: AuthProvider, provider_account_id: str) -> MockAccount | None:
        """소셜 로그인 정보로 계정 조회"""
        for account in self._storage.values():
            if account.auth_provider == provider and account.provider_account_id == provider_account_id:
                return account
        return None

    async def get_by_id(self, account_id: UUID) -> MockAccount | None:
        """계정 ID로 조회"""
        return self._storage.get(account_id)

    async def create(
        self,
        provider: AuthProvider,
        provider_account_id: str,
        email: str | None,
        nickname: str,
    ) -> MockAccount:
        """새 계정 생성"""
        account = MockAccount(
            id=uuid4(),
            auth_provider=provider,
            provider_account_id=provider_account_id,
            email=email,
            nickname=nickname,
        )
        self._storage[account.id] = account
        return account

    async def update_login_info(self, account: MockAccount, email: str | None, nickname: str) -> MockAccount:
        """로그인 시 최신 정보로 업데이트"""
        account.email = email
        account.nickname = nickname
        account.updated_at = datetime.now()
        return account

    async def deactivate(self, account: MockAccount) -> MockAccount:
        """계정 비활성화"""
        account.is_active = False
        account.updated_at = datetime.now()
        return account
