"""
Test OCR price endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

TEST_TOKEN = "test-ocr-token"


@pytest.fixture(autouse=True)
def set_admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TEST_TOKEN)
    from app.core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_ocr_preview_no_token_returns_401(client: AsyncClient):
    resp = await client.post("/api/v1/admin/prices/ocr-preview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ocr_save_no_token_returns_401(client: AsyncClient):
    resp = await client.post("/api/v1/admin/prices/ocr-save", json={"items": []})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ocr_preview_with_image(client: AsyncClient):
    """ocr-preview endpoint accepts an image and returns extracted text + parsed items."""
    mock_text = "بيض مخصب ابيض شركات 15\nبيض مخصب ساسو 11"
    mock_items = [
        {"product_type": "fertilized_eggs", "category": "white", "raw_product_name": "بيض مخصب ابيض شركات 15", "price": 15.0, "unit": "per_unit"},
        {"product_type": "fertilized_eggs", "category": "sasso", "raw_product_name": "بيض مخصب ساسو 11", "price": 11.0, "unit": "per_unit"},
    ]
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, mock_text, None),
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=(
            [{"product_type": "fertilized_eggs", "category": "white", "raw_line": "بيض مخصب ابيض شركات 15", "price": 15.0, "unit": "per_unit", "product_group": "fertilized_eggs"},
             {"product_type": "fertilized_eggs", "category": "sasso", "raw_line": "بيض مخصب ساسو 11", "price": 11.0, "unit": "per_unit", "product_group": "fertilized_eggs"}],
            [],
        ),
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", b"fake-png-data", "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "بيض مخصب" in data["extracted_text"]
        assert len(data["parsed_items"]) == 2
        assert data["parsed_items"][0]["price"] == 15.0


@pytest.mark.asyncio
async def test_ocr_preview_non_image_rejected(client: AsyncClient):
    """Non-image file upload should return an error."""
    resp = await client.post(
        "/api/v1/admin/prices/ocr-preview",
        files={"image": ("test.txt", b"not an image", "text/plain")},
        data={"recorded_date": "2026-06-01"},
        headers={"X-Admin-Token": TEST_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "صورة" in data["error"]


@pytest.mark.asyncio
async def test_ocr_preview_no_items_returns_empty(client: AsyncClient):
    """ocr-preview with no parseable items returns empty items list."""
    mock_text = "نص عادي لا يحتوي على أسعار"
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, mock_text, None),
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=([], ["نص عادي لا يحتوي على أسعار"]),
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", b"fake-png", "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 0
        assert len(data["rejected_lines"]) == 1


@pytest.mark.asyncio
async def test_ocr_save_persists_items(client: AsyncClient):
    """ocr-save endpoint persists parsed items as PriceRecords."""
    from app.models import PriceRecord

    payload = {
        "items": [
            {"product_type": "fertilized_eggs", "category": "white", "raw_product_name": "بيض مخصب ابيض شركات", "price": 15.0, "unit": "per_unit"},
            {"product_type": "fertilized_eggs", "category": "sasso", "raw_product_name": "بيض مخصب ساسو", "price": 11.0, "unit": "per_unit"},
        ],
        "recorded_date": "2026-06-01",
    }

    added_records = []

    class FakeDB:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

        async def execute(self, *args, **kwargs):
            pass

        def add(self, record):
            added_records.append(record)

        async def commit(self):
            pass

        async def refresh(self, *args):
            pass

        def add_all(self, records):
            added_records.extend(records)

    fake_db = FakeDB()

    with patch("app.api.endpoints.admin.get_db") as mock_get_db:
        async def gen():
            yield fake_db
        mock_get_db.return_value = gen()

        resp = await client.post(
            "/api/v1/admin/prices/ocr-save",
            json=payload,
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["saved_count"] == 2
