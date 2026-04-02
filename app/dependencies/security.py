from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.accounts import Account
from app.models.users import User
from app.repositories.account_repository import AccountRepository
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.utils.jwt.exceptions import TokenError
from app.utils.jwt.tokens import AccessToken

security = HTTPBearer()


async def get_current_account(
    credential: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> Account:
    """
    OAuth 로그인 사용자 인증 의존성

    Authorization 헤더에서 JWT Access Token을 검증하고 Account 반환
    """
    try:
        token = AccessToken(token=credential.credentials)
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


# 기존 User 기반 인증 (레거시 호환용)
async def get_request_user(credential: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> User:
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    user_id = verified.payload["user_id"]
    user = await UserRepository().get_user(user_id)
    if not user:
        raise HTTPException(detail="Authenticate Failed.", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
