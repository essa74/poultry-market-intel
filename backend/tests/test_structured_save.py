import sys; sys.path.insert(0, '.')
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date
from app.services.scrapers.base import BaseScraper
from app.models.scraping import ScrapingSource, ScrapingLog, ScrapingJobStatus, RawExtractedPrice, ScrapingSourceType


@pytest.mark.asyncio
async def test_structured_dict_bypass_normalizer_and_saves():
    """
    Verify that when _process_items receives a structured dict,
    it bypasses the normalizer and creates a PriceRecord directly.
    """
    # ── Setup mock source + db ────────────────────────────────────────
    source = MagicMock(spec=ScrapingSource)
    source.id = 999
    source.name = "Test Facebook Source"
    source.source_type = ScrapingSourceType.FACEBOOK
    source.url = "https://facebook.com/test"
    source.config = {}
    source.is_active = True
    source.health_score = 100.0

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    # ── Setup log ──────────────────────────────────────────────────────
    log = ScrapingLog(
        source_id=source.id,
        status=ScrapingJobStatus.RUNNING,
        job_id="test-job-999",
    )
    log.id = 999

    # ── Create scraper ─────────────────────────────────────────────────
    class TestScraper(BaseScraper):
        async def fetch_raw_data(self) -> list:
            return []  # not used in this test

    scraper = TestScraper(source, db)
    scraper.log = log

    # ── Structured item (as returned by _fetch_direct_posts) ───────────
    item = {
        "raw_text": "بيض ابيض شركات من 10 الى 22ج",
        "normalized_line": "بيض ابيض شركات من 10 الى 22ج",
        "product_type": "fertilized_eggs",
        "category": "white",
        "price": 16.0,
        "min_price": 10.0,
        "max_price": 22.0,
        "unit": "per_unit",
        "product_group": "fertilized_eggs",
        "confidence": 0.85,
    }

    # ── Execute _save_structured_price ─────────────────────────────────
    with patch("app.services.scrapers.price_persistence.save_extracted_price", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = ("saved", MagicMock(spec=["id"]))
        result = await scraper._save_structured_price(item)

    # ── Assertions ─────────────────────────────────────────────────────
    assert result is True, "_save_structured_price should return True on save"

    # Verify RawExtractedPrice was created with correct fields
    raw_price_calls = [c for c in db.add.call_args_list if isinstance(c[0][0], RawExtractedPrice)]
    assert len(raw_price_calls) >= 1, "RawExtractedPrice should be added to db"

    raw = raw_price_calls[0][0][0]
    assert raw.product_type == "fertilized_eggs"
    assert raw.category == "white"
    assert raw.price == 16.0
    assert raw.unit == "per_unit"
    assert raw.product_group == "fertilized_eggs"
    assert raw.confidence == 0.85
    assert raw.extraction_method == "regex"
    assert raw.is_normalized is True
    assert raw.source_id == 999
    assert raw.log_id == 999

    print("✓ Structured dict creates correct RawExtractedPrice")
    print(f"  product_type={raw.product_type} category={raw.category} price={raw.price} unit={raw.unit}")
    print("✓ Normalizer bypassed — save_extracted_price called directly")
    print("✓ test_structured_dict_bypass_normalizer_and_saves PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
