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
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
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
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
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


def _minimal_png() -> bytes:
    """Generate a minimal valid 1x1 red PNG."""
    import struct
    import zlib

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\x00\x00")
    idat = chunk(b"IDAT", raw)
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _minimal_jpg() -> bytes:
    """Generate a minimal valid JPEG (1x1 grey pixel)."""
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x12, 0x21, 0x31,
        0x41, 0x06, 0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91,
        0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33,
        0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26,
        0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43,
        0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57,
        0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73,
        0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A,
        0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4,
        0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
        0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA,
        0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2,
        0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xC0, 0x00, 0x0B,
        0x08, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xDA, 0x00,
        0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0x7B, 0x94, 0x11, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF,
        0xD9,
    ])


@pytest.mark.asyncio
async def test_ocr_preview_png_upload(client: AsyncClient):
    """PNG image upload returns parsed items."""
    png_data = _minimal_png()
    mock_text = "بيض مخصب ابيض 15"
    with patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, mock_text, None),
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=(
            [{"product_type": "fertilized_eggs", "category": "white", "raw_line": "بيض مخصب ابيض 15", "price": 15.0, "unit": "per_unit", "product_group": "fertilized_eggs"}],
            [],
        ),
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", png_data, "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 1


@pytest.mark.asyncio
async def test_ocr_preview_jpg_upload(client: AsyncClient):
    """JPEG image upload returns parsed items."""
    jpg_data = _minimal_jpg()
    mock_text = "بيض مخصب ساسو 11"
    with patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, mock_text, None),
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=(
            [{"product_type": "fertilized_eggs", "category": "sasso", "raw_line": "بيض مخصب ساسو 11", "price": 11.0, "unit": "per_unit", "product_group": "fertilized_eggs"}],
            [],
        ),
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.jpg", jpg_data, "image/jpeg")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 1


@pytest.mark.asyncio
async def test_ocr_preview_corrupted_image(client: AsyncClient):
    """Corrupted image upload returns an error."""
    resp = await client.post(
        "/api/v1/admin/prices/ocr-preview",
        files={"image": ("test.png", b"not-a-real-image-data", "image/png")},
        data={"recorded_date": "2026-06-01"},
        headers={"X-Admin-Token": TEST_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_ocr_preview_unsupported_format(client: AsyncClient):
    """Unsupported image format (gif) returns an error."""
    resp = await client.post(
        "/api/v1/admin/prices/ocr-preview",
        files={"image": ("test.gif", b"GIF89a", "image/gif")},
        data={"recorded_date": "2026-06-01"},
        headers={"X-Admin-Token": TEST_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


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
