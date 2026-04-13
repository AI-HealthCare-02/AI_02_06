import os
import secrets
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


# 로컬/개발 환경용 기본값 (운영 환경에서는 사용 불가)
_DEFAULT_SECRET_KEY = f"dev-only-secret-key-{secrets.token_hex(16)}"
_DEFAULT_DB_PASSWORD = "pw1234"
_DEFAULT_KAKAO_CLIENT_ID = "mock_kakao_client_id"
_DEFAULT_KAKAO_CLIENT_SECRET = "mock_kakao_client_secret"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "root"
    DB_PASSWORD: str = _DEFAULT_DB_PASSWORD
    DB_NAME: str = "downforce_db"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    COOKIE_DOMAIN: str = "localhost"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"  # CORS 허용 도메인

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # LLM (OpenAI)
    OPENAI_API_KEY: str | None = None

    # Kakao OAuth (Mock 기본값)
    KAKAO_CLIENT_ID: str = _DEFAULT_KAKAO_CLIENT_ID
    KAKAO_CLIENT_SECRET: str = _DEFAULT_KAKAO_CLIENT_SECRET
    KAKAO_REDIRECT_URI: str = "http://localhost:3000/auth/kakao/callback"

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
