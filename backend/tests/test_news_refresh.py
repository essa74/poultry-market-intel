"""
Test news refresh endpoint and duplicate handling.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_news_refresh_returns_inserted_and_duplicates(client: AsyncClient):
    """POST /api/v1/news/refresh returns inserted and duplicates_skipped counts."""
    mock_result = {"inserted": 5, "duplicates_skipped": 3}
    with patch(
        "app.api.endpoints.news.refresh_all_news",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post("/api/v1/news/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["inserted"] == 5
        assert data["duplicates_skipped"] == 3
        assert "تم تحديث الأخبار" in data["message"]


@pytest.mark.asyncio
async def test_news_refresh_zero_inserts(client: AsyncClient):
    """POST /api/v1/news/refresh works when no new articles found."""
    mock_result = {"inserted": 0, "duplicates_skipped": 0}
    with patch(
        "app.api.endpoints.news.refresh_all_news",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post("/api/v1/news/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["inserted"] == 0
        assert data["duplicates_skipped"] == 0


@pytest.mark.asyncio
async def test_news_refresh_all_duplicates(client: AsyncClient):
    """POST /api/v1/news/refresh handles all-duplicates case without crash."""
    mock_result = {"inserted": 0, "duplicates_skipped": 10}
    with patch(
        "app.api.endpoints.news.refresh_all_news",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post("/api/v1/news/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["inserted"] == 0
        assert data["duplicates_skipped"] == 10


@pytest.mark.asyncio
async def test_news_refresh_backend_error(client: AsyncClient):
    """POST /api/v1/news/refresh returns 500 with detail on crash."""
    with patch(
        "app.api.endpoints.news.refresh_all_news",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB connection lost"),
    ):
        resp = await client.post("/api/v1/news/refresh")
        assert resp.status_code == 500
        data = resp.json()
        assert "detail" in data
