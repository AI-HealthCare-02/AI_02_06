"""앱 기본 테스트"""

import pytest
from httpx import AsyncClient

from app.main import app


def test_app_created():
    """FastAPI 앱 인스턴스 생성 확인"""
    assert app is not None
    assert app.title == "FastAPI"


class TestDocs:
    """API 문서 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_openapi_endpoint(self, client: AsyncClient):
        """OpenAPI 스키마 접근"""
        response = await client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "openapi" in data

    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client: AsyncClient):
        """Swagger UI 접근"""
        response = await client.get("/api/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_endpoint(self, client: AsyncClient):
        """ReDoc 접근"""
        response = await client.get("/api/redoc")
        assert response.status_code == 200
