import os
import secrets
import zoneinfo
from enum import StrEnum
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


# ============================================================
# 환경별 URL 설정 (ENV 값에 따라 자동 적용)
# ============================================================
# local/dev: 로컬 Docker 환경 (동일한 설정, 로그인 버튼만 다름)
# prod: EC2 + Vercel 배포 환경
_ENV_URLS = {
    Env.LOCAL: {
        # Local 환경: 로컬 Docker (dev 로그인 버튼 표시)
        "COOKIE_DOMAIN": "localhost",
        "API_BASE_URL": "http://localhost:8000",
        "FRONTEND_URL": "http://localhost:3000",
        "KAKAO_REDIRECT_URI": "http://localhost:3000/auth/kakao/callback",
    },
    Env.DEV: {
        # Dev 환경: 로컬 Docker (dev 로그인 버튼 숨김, 카카오 테스트용)
        "COOKIE_DOMAIN": "localhost",
        "API_BASE_URL": "http://localhost:8000",
        "FRONTEND_URL": "http://localhost:3000",
        "KAKAO_REDIRECT_URI": "http://localhost:3000/auth/kakao/callback",
    },
    Env.PROD: {
        # Prod 환경: EC2 백엔드 + Vercel 프론트엔드
        "COOKIE_DOMAIN": None,  # Vercel 도메인용 (크로스 도메인 쿠키)
        "API_BASE_URL": "http://52.78.62.12",
        "FRONTEND_URL": "https://ai-02-06.vercel.app",
        "KAKAO_REDIRECT_URI": "https://ai-02-06.vercel.app/auth/kakao/callback",
    },
}

# 로컬/개발 환경용 기본값 (운영 환경에서는 사용 불가)
_DEFAULT_SECRET_KEY = f"dev-only-secret-key-{secrets.token_hex(16)}"
_DEFAULT_DB_PASSWORD = "downforce_admin"
_DEFAULT_KAKAO_CLIENT_ID = "mock_kakao_client_id"
_DEFAULT_KAKAO_CLIENT_SECRET = "mock_kakao_client_secret"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    TIMEZONE: zoneinfo.ZoneInfo = Field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    # DB 설정 (ENV에 따라 자동 설정되지 않음 - 민감 정보)
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_USER: str = "downforce_admin"
    DB_PASSWORD: str = _DEFAULT_DB_PASSWORD
    DB_NAME: str = "downforce_db"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    # URL 설정 (ENV에 따라 자동 설정됨, .env에서 개별 지정도 가능)
    COOKIE_DOMAIN: str | None = None
    API_BASE_URL: str | None = None
    FRONTEND_URL: str | None = None

    # JWT 설정
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # LLM (OpenAI)
    OPENAI_API_KEY: str | None = None

    # Kakao OAuth (충돌 마커 제거 완료)
    KAKAO_CLIENT_ID: str = _DEFAULT_KAKAO_CLIENT_ID
    KAKAO_CLIENT_SECRET: str = _DEFAULT_KAKAO_CLIENT_SECRET
    KAKAO_REDIRECT_URI: str | None = None

    @model_validator(mode="after")
    def apply_env_defaults(self) -> "Config":
        """ENV에 따라 URL 기본값 자동 적용 (.env에서 개별 지정하면 우선)"""
        env_urls = _ENV_URLS.get(self.ENV, _ENV_URLS[Env.LOCAL])

        # .env에서 지정하지 않은 값만 자동 설정
        if self.COOKIE_DOMAIN is None:
            self.COOKIE_DOMAIN = env_urls["COOKIE_DOMAIN"]
        if self.API_BASE_URL is None:
            self.API_BASE_URL = env_urls["API_BASE_URL"]
        if self.FRONTEND_URL is None:
            self.FRONTEND_URL = env_urls["FRONTEND_URL"]
        if self.KAKAO_REDIRECT_URI is None:
            self.KAKAO_REDIRECT_URI = env_urls["KAKAO_REDIRECT_URI"]

        return self

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Config":
        """운영 환경에서 기본값 사용 시 에러 발생"""
        if self.ENV == Env.PROD:
            errors = []

            if self.SECRET_KEY == _DEFAULT_SECRET_KEY or self.SECRET_KEY.startswith("dev-only-"):
                errors.append("SECRET_KEY must be set in production environment")

            if self.DB_PASSWORD == _DEFAULT_DB_PASSWORD:
                errors.append("DB_PASSWORD must be set in production environment")

            if self.KAKAO_CLIENT_ID == _DEFAULT_KAKAO_CLIENT_ID:
                errors.append("KAKAO_CLIENT_ID must be set in production environment")

            if self.KAKAO_CLIENT_SECRET == _DEFAULT_KAKAO_CLIENT_SECRET:
                errors.append("KAKAO_CLIENT_SECRET must be set in production environment")

            if errors:
                raise ValueError(f"Production configuration errors: {'; '.join(errors)}")

        return self


# 싱글톤 인스턴스
config = Config()
