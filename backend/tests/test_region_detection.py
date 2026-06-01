"""
Test smart region detection for poultry price posters.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app

TEST_TOKEN = "test-region-token"


@pytest.fixture(autouse=True)
def set_admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TEST_TOKEN)
    from app.core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _minimal_png() -> bytes:
    import struct, zlib
    def chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 10, 10, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00" + b"\xff\x00\x00" * 100)
    idat = chunk(b"IDAT", raw)
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.mark.asyncio
async def test_region_detection_no_token_returns_401(client: AsyncClient):
    resp = await client.post("/api/v1/admin/prices/ocr-preview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_region_detection_fallback_when_text_empty(client: AsyncClient):
    """When both egg and chick parsers return nothing, region detection runs."""
    png = _minimal_png()
    mock_regions = [
        {
            "product_type": "day_old_chicks",
            "category": "white",
            "raw_product_name": "أبيض شركات",
            "price": 25.0,
            "unit": "per_unit",
            "confidence": "high",
            "confidence_reason": "region detection: 'أبيض شركات' label near price 25.0",
            "extraction_method": "region_detection",
        }
    ]
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, "نص بدون أسعار", None),
    ), patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.chick_poster_parser._is_chick_poster",
        return_value=False,
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=([], ["نص بدون أسعار"]),
    ), patch(
        "app.services.chick_poster_parser.parse_chick_poster_text",
        return_value=([], ["نص بدون أسعار"]),
    ), patch(
        "app.services.region_detection.detect_regions",
        new_callable=AsyncMock,
        return_value=mock_regions,
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", png, "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 1
        assert data["parsed_items"][0]["extraction_method"] == "region_detection"
        assert data["parsed_items"][0]["price"] == 25.0
        assert data["parsed_items"][0]["confidence"] == "high"


@pytest.mark.asyncio
async def test_region_detection_low_confidence_when_no_label(client: AsyncClient):
    """Region detection without a nearby label returns low confidence."""
    png = _minimal_png()
    mock_regions = [
        {
            "product_type": "day_old_chicks",
            "category": "white",
            "raw_product_name": "سعر 18.0",
            "price": 18.0,
            "unit": "per_unit",
            "confidence": "low",
            "confidence_reason": "region detection: price 18.0 found, no label nearby",
            "extraction_method": "region_detection",
        }
    ]
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, "نص بدون أسعار", None),
    ), patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.chick_poster_parser._is_chick_poster",
        return_value=False,
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=([], ["نص بدون أسعار"]),
    ), patch(
        "app.services.chick_poster_parser.parse_chick_poster_text",
        return_value=([], ["نص بدون أسعار"]),
    ), patch(
        "app.services.region_detection.detect_regions",
        new_callable=AsyncMock,
        return_value=mock_regions,
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", png, "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 1
        assert data["parsed_items"][0]["confidence"] == "low"


@pytest.mark.asyncio
async def test_table_ocr_still_works_when_has_results(client: AsyncClient):
    """When table OCR finds items, region detection is NOT triggered."""
    png = _minimal_png()
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, "بيض مخصب ابيض شركات 15", None),
    ), patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.chick_poster_parser._is_chick_poster",
        return_value=False,
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=(
            [{"product_type": "fertilized_eggs", "category": "white", "raw_line": "بيض مخصب ابيض شركات 15", "price": 15.0, "unit": "per_unit", "product_group": "fertilized_eggs"}],
            [],
        ),
    ), patch(
        "app.services.chick_poster_parser.parse_chick_poster_text",
        return_value=([], []),
    ), patch(
        "app.services.region_detection.detect_regions",
        new_callable=AsyncMock,
    ) as mock_region:
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", png, "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["parsed_items"]) == 1
        assert data["parsed_items"][0]["extraction_method"] == "table_ocr"
        mock_region.assert_not_called()


@pytest.mark.asyncio
async def test_region_detection_extraction_method_in_response(client: AsyncClient):
    """parsed_items from region detection include extraction_method field."""
    png = _minimal_png()
    mock_regions = [
        {
            "product_type": "day_old_chicks",
            "category": "sasso",
            "raw_product_name": "ساسو",
            "price": 22.0,
            "unit": "per_unit",
            "confidence": "high",
            "confidence_reason": "region detection: 'ساسو' label near price 22.0",
            "extraction_method": "region_detection",
        }
    ]
    with patch(
        "app.services.ocr_service.ocr_image",
        new_callable=AsyncMock,
        return_value=(True, "نص عشوائي", None),
    ), patch(
        "app.services.ocr_service.validate_image",
        return_value=(True, None),
    ), patch(
        "app.services.chick_poster_parser._is_chick_poster",
        return_value=False,
    ), patch(
        "app.services.scrapers.facebook_scraper._parse_arabic_price_lines",
        return_value=([], ["نص عشوائي"]),
    ), patch(
        "app.services.chick_poster_parser.parse_chick_poster_text",
        return_value=([], ["نص عشوائي"]),
    ), patch(
        "app.services.region_detection.detect_regions",
        new_callable=AsyncMock,
        return_value=mock_regions,
    ):
        resp = await client.post(
            "/api/v1/admin/prices/ocr-preview",
            files={"image": ("test.png", png, "image/png")},
            data={"recorded_date": "2026-06-01"},
            headers={"X-Admin-Token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["parsed_items"][0]["extraction_method"] == "region_detection"


@pytest.mark.asyncio
async def test_no_false_save_without_preview(client: AsyncClient):
    """Ensure ocr-save endpoint requires explicit items, not auto-saving."""
    resp = await client.post(
        "/api/v1/admin/prices/ocr-save",
        json={"items": []},
        headers={"X-Admin-Token": TEST_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved_count"] == 0
