"""
Account Repository (Mock 버전)

JSON 파일에서 초기 데이터를 로드하고 메모리에 저장합니다.
나중에 DB 연동 시 Tortoise ORM 버전으로 교체하면 됩니다.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.models.accounts import AuthProvider

# Mock 데이터 경로
MOCK_DATA_DIR = Path(__file__).parent.parent / "tests" / "mock_data"


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

    # 클래스 변수로 메모리 저장소
    _storage: dict[UUID, MockAccount] = {}
    _initialized: bool = False

    def __init__(self) -> None:
        # 최초 1회만 JSON에서 데이터 로드
        if not AccountRepository._initialized:
            self._load_mock_data()
            AccountRepository._initialized = True

    def _load_mock_data(self) -> None:
        """JSON 파일에서 초기 계정 데이터 로드"""
        accounts_file = MOCK_DATA_DIR / "app_accounts.json"
        if not accounts_file.exists():
            return

        data = json.loads(accounts_file.read_text(encoding="utf-8"))

        for acc in data.get("accounts", []):
            account = MockAccount(
                id=UUID(acc["id"]),
                auth_provider=acc["auth_provider"],
                provider_account_id=acc["provider_account_id"],
                email=acc.get("email"),
                nickname=acc["nickname"],
                is_active=acc.get("is_active", True),
            )
            self._storage[account.id] = account

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
