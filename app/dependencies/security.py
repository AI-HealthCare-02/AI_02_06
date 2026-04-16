"""Security dependencies module.

This module provides authentication and authorization dependencies
for FastAPI endpoints, including JWT token validation and user extraction.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.accounts import Account
from app.repositories.account_repository import AccountRepository
from app.utils.jwt.exceptions import TokenError
from app.utils.jwt.tokens import AccessToken

# Authorization header is optional (cookie takes priority)
security = HTTPBearer(auto_error=False)


def _extract_token(request: Request, credential: HTTPAuthorizationCredentials | None) -> str:
    """Extract token with cookie priority and Authorization header fallback.

    Uses HttpOnly cookie first for XSS prevention, falls back to Authorization
    header if cookie is not available (for API client compatibility).

    Args:
        request: FastAPI request object.
        credential: HTTP authorization credentials from header.

    Returns:
        str: Extracted JWT token.

    Raises:
        HTTPException: If no token found in either cookie or header.
    """
    # 1. Check access_token in cookie (priority)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # 2. Check Authorization header (fallback)
    if credential and credential.credentials:
        return credential.credentials

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "missing_token",
            "error_description": "Authentication token is required.",
        },
    )


async def get_current_account(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Account:
    """OAuth login user authentication dependency.

    Validates JWT Access Token from HttpOnly cookie or Authorization header
    and returns the authenticated Account.

    Args:
        request: FastAPI request object.
        credential: HTTP authorization credentials from header.

    Returns:
        Account: Authenticated user account.

    Raises:
        HTTPException: If token is invalid, account not found, or account disabled.
    """
    token_str = _extract_token(request, credential)

    try:
        token = AccessToken(token=token_str)
    except TokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "error_description": "Invalid token.",
            },
        ) from err

    # Extract account_id from sub claim
    account_id_str = token.payload.get("sub")
    if not account_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "error_description": "Token does not contain user information.",
            },
        )

    try:
        account_id = UUID(account_id_str)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "error_description": "Invalid token format.",
            },
        ) from err

    account = await AccountRepository().get_by_id(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "account_not_found",
                "error_description": "Account not found.",
            },
        )

    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_disabled",
                "error_description": "Account is disabled.",
            },
        )

    return account
