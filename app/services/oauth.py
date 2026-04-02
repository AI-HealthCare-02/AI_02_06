"""
OAuth 인증 서비스

개발/테스트: 자체 Mock 서버(mock_oauth_routers.py)와 HTTP 통신
운영: 실제 카카오 서버와 HTTP 통신
"""

import time

import httpx
from fastapi import HTTPException, status

from app.core import config
from app.core.config import Env
from app.models.accounts import AuthProvider
from app.repositories.account_repository import AccountRepository, MockAccount
from app.utils.jwt.tokens import AccessToken, RefreshToken


class OAuthService:
    """OAuth 인증 서비스"""

    # Rate limiting 추적 (IP -> (count, timestamp))
    _rate_limit_tracker: dict[str, tuple[int, float]] = {}
    RATE_LIMIT_MAX = 10
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(self) -> None:
        self.account_repo = AccountRepository()

        # 환경에 따른 타겟 URL 동적 할당
        if config.ENV == Env.PROD:
            self.kakao_token_url = "https://kauth.kakao.com/oauth/token"
            self.kakao_userinfo_url = "https://kapi.kakao.com/v2/user/me"
        else:
            # 설정된 API_BASE_URL(예: http://localhost:8000)을 기반으로 Mock 라우터 지정
            self.kakao_token_url = f"{config.API_BASE_URL}/api/v1/mock/kakao/oauth/token"
            self.kakao_userinfo_url = f"{config.API_BASE_URL}/api/v1/mock/kakao/v2/user/me"

    def _check_rate_limit(self, client_ip: str) -> None:
        """Rate limit 체크"""
        current_time = time.time()

        if client_ip in self._rate_limit_tracker:
            count, timestamp = self._rate_limit_tracker[client_ip]

            if current_time - timestamp > self.RATE_LIMIT_WINDOW:
                self._rate_limit_tracker[client_ip] = (1, current_time)
                return

            if count >= self.RATE_LIMIT_MAX:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "error_description": f"요청 횟수를 초과했습니다. {self.RATE_LIMIT_WINDOW}초 후에 다시 시도해주세요.",
                    },
                )

            self._rate_limit_tracker[client_ip] = (count + 1, timestamp)
        else:
            self._rate_limit_tracker[client_ip] = (1, current_time)

    async def _exchange_code_for_token(self, code: str) -> dict:
        """인가 코드로 카카오(또는 Mock) 서버와 통신하여 액세스 토큰 획득"""
        data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_CLIENT_ID,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "code": code.strip(),
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.kakao_token_url, data=data, timeout=5.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # 4xx, 5xx 등 서버에서 에러 응답을 준 경우
                error_detail = e.response.json() if e.response.content else {"error": "token_exchange_failed"}
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail,
                ) from e
            except httpx.RequestError as e:  # <--- 여기서 as e 추가
                # 네트워크 연결 실패, 타임아웃 등 물리적 통신 실패
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
            except httpx.RequestError as e:  # <--- 여기서 as e 추가
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "network_error",
                        "error_description": "사용자 정보 서버와 통신할 수 없습니다.",
                    },
                ) from e

    async def kakao_callback(self, code: str, client_ip: str) -> tuple[MockAccount, bool]:
        """
        카카오 콜백 처리 로직
        """
        self._check_rate_limit(client_ip)

        # 1. 인가 코드로 액세스 토큰 교환 (네트워크 통신)
        token_data = await self._exchange_code_for_token(code)
        kakao_access_token = token_data["access_token"]

        # 2. 액세스 토큰으로 사용자 정보 조회 (네트워크 통신)
        user_info = await self._get_user_info(kakao_access_token)

        # 사용자 정보 파싱
        provider_account_id = str(user_info["id"])
        kakao_account = user_info.get("kakao_account", {})
        email = kakao_account.get("email")
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", f"카카오유저_{provider_account_id[:4]}")

        # 3. DB 계정 조회 및 생성/업데이트 로직
        account = await self.account_repo.get_by_provider(
            provider=AuthProvider.KAKAO,
            provider_account_id=provider_account_id,
        )

        is_new_user = False

        if account:
            if not account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "account_disabled",
                        "error_description": "비활성화된 계정입니다. 고객센터에 문의해주세요.",
                    },
                )

            await self.account_repo.update_login_info(
                account=account,
                email=email,
                nickname=nickname,
            )
        else:
            account = await self.account_repo.create(
                provider=AuthProvider.KAKAO,
                provider_account_id=provider_account_id,
                email=email,
                nickname=nickname,
            )
            is_new_user = True

        return account, is_new_user

    def issue_tokens(self, account: MockAccount) -> dict[str, str]:
        """JWT 토큰 발급"""
        access_token = AccessToken()
        access_token["sub"] = str(account.id)
        access_token["provider"] = account.auth_provider

        refresh_token = RefreshToken()
        refresh_token["sub"] = str(account.id)

        return {
            "access_token": str(access_token),
            "refresh_token": str(refresh_token),
        }
