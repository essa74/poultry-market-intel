"""
Test admin token protection on sensitive endpoints.
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings


TEST_TOKEN = "test-admin-token-123"


@pytest.fixture(autouse=True)
def set_admin_token():
    """Set ADMIN_TOKEN env var for the duration of the test."""
    old = os.environ.get("ADMIN_TOKEN")
    os.environ["ADMIN_TOKEN"] = TEST_TOKEN
    # Clear the cached settings so it picks up the new env var
    get_settings.cache_clear()
    yield
    if old:
        os.environ["ADMIN_TOKEN"] = old
    else:
        os.environ.pop("ADMIN_TOKEN", None)
    get_settings.cache_clear()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_401(client: AsyncClient):
    """POST /api/v1/scraping/run without token should return 401."""
    resp = await client.post("/api/v1/scraping/run")
    assert resp.status_code == 401
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_protected_endpoint_with_wrong_token_returns_401(client: AsyncClient):
    """POST /api/v1/scraping/run with wrong Bearer token should return 401."""
    resp = await client.post(
        "/api/v1/scraping/run",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_correct_bearer_token_succeeds(client: AsyncClient):
    """POST /api/v1/scraping/run with correct Bearer token should pass dependency."""
    settings = get_settings()
    assert settings.admin_token == TEST_TOKEN
    resp = await client.post(
        "/api/v1/scraping/run",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code != 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_x_admin_token_succeeds(client: AsyncClient):
    """X-Admin-Token header should also work."""
    resp = await client.post(
        "/api/v1/scraping/run",
        headers={"X-Admin-Token": TEST_TOKEN},
    )
    assert resp.status_code != 401


@pytest.mark.asyncio
async def test_public_endpoint_returns_200_without_token(client: AsyncClient):
    """GET /health without token should return 200 (no DB, no admin token needed)."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
