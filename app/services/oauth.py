"""
OAuth 인증 서비스

개발/테스트: 자체 Mock 서버(mock_oauth_routers.py)와 HTTP 통신
운영: 실제 카카오 서버와 HTTP 통신
"""

import httpx
from fastapi import HTTPException, status

from app.core import config
from app.core.config import Env
from app.models.accounts import Account, AuthProvider
from app.repositories.account_repository import AccountRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.rate_limiter import RateLimiter
from app.utils.jwt.tokens import AccessToken, RefreshToken


class OAuthService:
    """OAuth 인증 서비스"""

    def __init__(
        self,
        account_repo: AccountRepository | None = None,
        refresh_token_repo: RefreshTokenRepository | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.account_repo = account_repo or AccountRepository()
        self.refresh_token_repo = refresh_token_repo or RefreshTokenRepository()
        self.rate_limiter = rate_limiter

        # 환경에 따른 타겟 URL 동적 할당
        if config.ENV == Env.PROD:
            self.kakao_token_url = "https://kauth.kakao.com/oauth/token"
            self.kakao_userinfo_url = "https://kapi.kakao.com/v2/user/me"
        else:
            self.kakao_token_url = f"{config.API_BASE_URL}/api/v1/mock/kakao/oauth/token"
            self.kakao_userinfo_url = f"{config.API_BASE_URL}/api/v1/mock/kakao/v2/user/me"

    def _check_rate_limit(self, client_ip: str) -> None:
        """Rate limit 체크 (rate_limiter가 주입된 경우에만 동작)"""
        if self.rate_limiter:
            self.rate_limiter.check(client_ip)

    async def _exchange_code_for_token(self, code: str) -> dict:
        """인가 코드로 카카오(또는 Mock) 서버와 통신하여 액세스 토큰 획득"""
        data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_CLIENT_ID,
            "client_secret": config.KAKAO_CLIENT_SECRET,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "code": code.strip(),
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.kakao_token_url, data=data, timeout=5.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json() if e.response.content else {"error": "token_exchange_failed"}
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail,
                ) from e
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "network_error",
                        "error_description": "인증 서버와 통신할 수 없습니다. 잠시 후 다시 시도해주세요.",
                    },
                ) from e

    async def _get_user_info(self, access_token: str) -> dict:
        """액세스 토큰으로 카카오(또는 Mock) 서버와 통신하여 사용자 정보 획득"""
        headers = {
            "Authorization": f"Bearer {access_token.strip()}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.kakao_userinfo_url, headers=headers, timeout=5.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json() if e.response.content else {"error": "userinfo_failed"}
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail,
                ) from e
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "network_error",
                        "error_description": "사용자 정보 서버와 통신할 수 없습니다.",
                    },
                ) from e

    async def kakao_callback(self, code: str, client_ip: str) -> tuple[Account, bool]:
        """
        카카오 콜백 처리 로직

        1. 인가 코드로 액세스 토큰 교환
        2. 액세스 토큰으로 사용자 정보 조회
        3. 계정 생성 또는 로그인 처리

        Returns:
            tuple[Account, bool]: (계정, 신규가입 여부)
        """
        self._check_rate_limit(client_ip)

        # 1. 인가 코드로 액세스 토큰 교환
        token_data = await self._exchange_code_for_token(code)
        kakao_access_token = token_data["access_token"]

        # 2. 액세스 토큰으로 사용자 정보 조회
        user_info = await self._get_user_info(kakao_access_token)

        # 사용자 정보 파싱
        provider_account_id = str(user_info["id"])
        kakao_account = user_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", f"카카오유저_{provider_account_id[:4]}")
        profile_image_url = profile.get("profile_image_url")

        # 3. DB 계정 조회
        account = await self.account_repo.get_by_provider(
            provider=AuthProvider.KAKAO,
            provider_account_id=provider_account_id,
        )

        is_new_user = False

        if account:
            # 기존 계정 - 활성 상태 체크
            if not account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "account_disabled",
                        "error_description": "비활성화된 계정입니다. 고객센터에 문의해주세요.",
                    },
                )

            # 최신 정보로 업데이트
            await self.account_repo.update_login_info(
                account=account,
                nickname=nickname,
                profile_image_url=profile_image_url,
            )
        else:
            # 신규 계정 생성
            account = await self.account_repo.create(
                provider=AuthProvider.KAKAO,
                provider_account_id=provider_account_id,
                nickname=nickname,
                profile_image_url=profile_image_url,
            )
            is_new_user = True

        return account, is_new_user

    async def issue_tokens(self, account: Account) -> dict[str, str]:
        """
        JWT 토큰 발급 및 refresh token DB 저장

        Returns:
            {"access_token": "...", "refresh_token": "..."}
        """
        # Access Token 생성
        access_token = AccessToken()
        access_token["sub"] = str(account.id)
        access_token["provider"] = account.auth_provider

        # Refresh Token 생성
        refresh_token = RefreshToken()
        refresh_token["sub"] = str(account.id)

        refresh_token_str = str(refresh_token)

        # Refresh Token DB 저장
        await self.refresh_token_repo.create(
            account_id=account.id,
            token=refresh_token_str,
        )

        return {
            "access_token": str(access_token),
            "refresh_token": refresh_token_str,
        }

    async def revoke_refresh_token(self, token: str) -> bool:
        """Refresh Token 무효화 (로그아웃)"""
        return await self.refresh_token_repo.revoke(token)
