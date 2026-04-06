from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.accounts import Account
from app.repositories.account_repository import AccountRepository
from app.utils.jwt.exceptions import TokenError
from app.utils.jwt.tokens import AccessToken

# Authorization 헤더는 선택적 (쿠키 우선)
security = HTTPBearer(auto_error=False)


def _extract_token(request: Request, credential: HTTPAuthorizationCredentials | None) -> str:
    """
    토큰 추출 (쿠키 우선, Authorization 헤더 폴백)

    XSS 방지를 위해 HttpOnly 쿠키를 우선 사용하고,
    쿠키가 없으면 Authorization 헤더에서 추출 (API 클라이언트 호환)
    """
    # 1. 쿠키에서 access_token 확인 (우선)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # 2. Authorization 헤더에서 확인 (폴백)
    if credential and credential.credentials:
        return credential.credentials

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "missing_token", "error_description": "인증 토큰이 필요합니다."},
    )


async def get_current_account(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Account:
    """
    OAuth 로그인 사용자 인증 의존성

    HttpOnly 쿠키 또는 Authorization 헤더에서 JWT Access Token을 검증하고 Account 반환
    """
    token_str = _extract_token(request, credential)

    try:
        token = AccessToken(token=token_str)
    except TokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "error_description": "유효하지 않은 토큰입니다."},
        ) from err

    # sub claim에서 account_id 추출
    account_id_str = token.payload.get("sub")
    if not account_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "error_description": "토큰에 사용자 정보가 없습니다."},
        )

    try:
        account_id = UUID(account_id_str)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "error_description": "잘못된 토큰 형식입니다."},
        ) from err

    account = await AccountRepository().get_by_id(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "account_not_found", "error_description": "계정을 찾을 수 없습니다."},
        )

    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "account_disabled", "error_description": "비활성화된 계정입니다."},
        )

    return account
