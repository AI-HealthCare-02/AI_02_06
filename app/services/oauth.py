"""
OAuth 인증 서비스

실제 배포 시에는 httpx로 카카오 서버와 통신합니다.
개발/테스트 시에는 Mock 카카오 서버와 통신합니다.
"""

import time

import httpx
from fastapi import HTTPException, status

from app.core import config
from app.models.accounts import AuthProvider
from app.repositories.account_repository import AccountRepository, MockAccount
from app.utils.jwt.tokens import AccessToken, RefreshToken


class KakaoOAuthClient:
    """카카오 OAuth API 클라이언트"""

    def __init__(self, base_url: str = "http://localhost:8000/mock/kakao"):
        """
        Args:
            base_url: 카카오 OAuth 서버 URL
                - 개발: http://localhost:8000/mock/kakao (Mock 서버)
                - 운영: https://kauth.kakao.com (실제 카카오)
        """
        self.base_url = base_url
        self.client_id = config.KAKAO_CLIENT_ID
        self.client_secret = config.KAKAO_CLIENT_SECRET
        self.redirect_uri = config.KAKAO_REDIRECT_URI

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        인가 코드로 액세스 토큰 교환

        Returns:
            {
                "access_token": "...",
                "token_type": "bearer",
                "refresh_token": "...",
                "expires_in": 21599,
                ...
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )

        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": error_data.get("error", "token_exchange_failed"),
                    "error_description": error_data.get("error_description", "토큰 교환에 실패했습니다."),
                },
            )

        return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """
        액세스 토큰으로 사용자 정보 조회

        Returns:
            {
                "id": 123456789,
                "kakao_account": {
                    "email": "user@kakao.com",
                    "profile": {
                        "nickname": "홍길동"
                    }
                }
            }
        """
        # Mock 서버는 /user, 실제 카카오는 다른 도메인의 /v2/user/me
        user_url = f"{self.base_url}/user"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                user_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": error_data.get("error", "user_info_failed"),
                    "error_description": error_data.get("error_description", "사용자 정보 조회에 실패했습니다."),
                },
            )

        return response.json()


class OAuthService:
    """OAuth 인증 서비스"""

    # Rate limiting 추적 (IP -> (count, timestamp))
    _rate_limit_tracker: dict[str, tuple[int, float]] = {}
    RATE_LIMIT_MAX = 10
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(self) -> None:
        self.account_repo = AccountRepository()
        self.kakao_client = KakaoOAuthClient()

    def _check_rate_limit(self, client_ip: str) -> None:
        """Rate limit 체크"""
        current_time = time.time()

        if client_ip in self._rate_limit_tracker:
            count, timestamp = self._rate_limit_tracker[client_ip]

            # 윈도우 시간이 지났으면 리셋
            if current_time - timestamp > self.RATE_LIMIT_WINDOW:
                self._rate_limit_tracker[client_ip] = (1, current_time)
                return

            # 제한 초과 체크
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

    async def kakao_callback(self, code: str, client_ip: str) -> tuple[MockAccount, bool]:
        """
        카카오 콜백 처리

        1. 인가 코드로 액세스 토큰 교환
        2. 액세스 토큰으로 사용자 정보 조회
        3. 계정 생성 또는 로그인 처리

        Returns:
            tuple[Account, bool]: (계정, 신규가입 여부)
        """
        # Rate limit 체크
        self._check_rate_limit(client_ip)

        # 1. 인가 코드로 액세스 토큰 교환
        token_data = await self.kakao_client.exchange_code_for_token(code)
        kakao_access_token = token_data["access_token"]

        # 2. 액세스 토큰으로 사용자 정보 조회
        user_info = await self.kakao_client.get_user_info(kakao_access_token)

        # 사용자 정보 파싱
        provider_account_id = str(user_info["id"])
        kakao_account = user_info.get("kakao_account", {})
        email = kakao_account.get("email")
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", f"카카오유저_{provider_account_id[:4]}")

        # 3. 기존 계정 조회
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
                email=email,
                nickname=nickname,
            )
        else:
            # 신규 계정 생성
            account = await self.account_repo.create(
                provider=AuthProvider.KAKAO,
                provider_account_id=provider_account_id,
                email=email,
                nickname=nickname,
            )
            is_new_user = True

        return account, is_new_user

    def issue_tokens(self, account: MockAccount) -> dict[str, AccessToken | RefreshToken]:
        """JWT 토큰 발급"""
        access_token = AccessToken.create(
            sub=str(account.id),
            extra_claims={"provider": account.auth_provider},
        )
        refresh_token = RefreshToken.create(sub=str(account.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
