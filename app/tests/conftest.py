"""테스트 설정 - Tortoise ORM 초기화 및 공통 fixture"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core import config
from app.db.databases import TORTOISE_APP_MODELS
from app.main import app

TEST_BASE_URL = "http://test"


def get_test_tortoise_config() -> dict:
    """CI 환경용 Tortoise ORM 설정"""
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": config.DB_HOST,
                    "port": config.DB_PORT,
                    "user": config.DB_USER,
                    "password": config.DB_PASSWORD,
                    "database": config.DB_NAME,
                },
            },
        },
        "apps": {
            "models": {
                "models": TORTOISE_APP_MODELS,
                "default_connection": "default",
            },
        },
        "timezone": "Asia/Seoul",
    }


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """세션 스코프 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_db() -> AsyncGenerator[None, None]:
    """테스트 DB 초기화 (세션 스코프)"""
    tortoise_config = get_test_tortoise_config()
    await Tortoise.init(config=tortoise_config)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """비동기 테스트 클라이언트"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=TEST_BASE_URL,
    ) as ac:
        yield ac
