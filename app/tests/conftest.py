"""테스트 설정 - 공통 fixture"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_BASE_URL = "http://test"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """비동기 테스트 클라이언트"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=TEST_BASE_URL,
    ) as ac:
        yield ac
