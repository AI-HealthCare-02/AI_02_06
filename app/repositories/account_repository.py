"""Account repository module.

This module provides data access layer for the accounts table,
handling social login account management operations.
"""

from uuid import UUID, uuid4

from app.models.accounts import Account, AuthProvider


class AccountRepository:
    """Account database repository for social login management."""

    async def get_by_provider(self, provider: AuthProvider, provider_account_id: str) -> Account | None:
        """Get account by social login provider information.

        Args:
            provider: Authentication provider.
            provider_account_id: Provider account ID.

        Returns:
            Account | None: Account if found, None otherwise.
        """
        return await Account.filter(
            auth_provider=provider,
            provider_account_id=provider_account_id,
            deleted_at__isnull=True,
        ).first()

    async def get_by_id(self, account_id: UUID) -> Account | None:
        """Get account by ID.

        Args:
            account_id: Account UUID.

        Returns:
            Account | None: Account if found, None otherwise.
        """
        return await Account.filter(
            id=account_id,
            deleted_at__isnull=True,
        ).first()

    async def create(
        self,
        provider: AuthProvider,
        provider_account_id: str,
        nickname: str,
        profile_image_url: str | None = None,
    ) -> Account:
        """Create new account.

        Args:
            provider: Authentication provider.
            provider_account_id: Provider account ID.
            nickname: User nickname.
            profile_image_url: Optional profile image URL.

        Returns:
            Account: Created account.
        """
        return await Account.create(
            id=uuid4(),
            auth_provider=provider,
            provider_account_id=provider_account_id,
            nickname=nickname,
            profile_image_url=profile_image_url,
            is_active=True,
        )

    async def update_login_info(
        self,
        account: Account,
        nickname: str,
        profile_image_url: str | None = None,
    ) -> Account:
        """Update account with latest login information.

        Args:
            account: Account to update.
            nickname: Updated nickname.
            profile_image_url: Updated profile image URL.

        Returns:
            Account: Updated account.
        """
        account.nickname = nickname
        account.profile_image_url = profile_image_url
        await account.save()
        return account

    async def deactivate(self, account: Account) -> Account:
        """Deactivate account.

        Args:
            account: Account to deactivate.

        Returns:
            Account: Deactivated account.
        """
        account.is_active = False
        await account.save()
        return account
