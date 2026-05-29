"""
Telegram channel scraper.
Scrapes public Telegram channels via t.me or tg channel web preview.
"""
import logging
import re
from typing import Optional
from httpx import AsyncClient
from bs4 import BeautifulSoup
from .base import BaseScraper
from .config import get_scraper_settings

logger = logging.getLogger(__name__)


class TelegramChannelScraper(BaseScraper):
    async def fetch_raw_data(self) -> list[str]:
        items = []
        config = self.source.config or {}
        channel = config.get("channel", "")
        limit = config.get("message_limit", 50)

        if not channel:
            import re as _re
            m = _re.search(r"t\.me/s?/(\w+)", self.source.url)
            channel = m.group(1) if m else ""
            if channel:
                logger.info(f"Derived channel '{channel}' from source URL")
                correct_url = f"https://t.me/s/{channel}"
                if self.source.url != correct_url:
                    self.source.url = correct_url
                    logger.info(f"Normalized source URL to {correct_url}")
            else:
                logger.warning(f"No channel configured for Telegram source {self.source.id}")
                return items

        try:
            async with AsyncClient(
                timeout=get_scraper_settings().request_timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                },
                follow_redirects=True,
            ) as client:
                url = f"https://t.me/s/{channel}"
                resp = await client.get(url)
                resp.raise_for_status()

                self.raw_content = resp.text
                logger.info(f"Fetched {url}: {len(resp.text)} bytes")

                soup = BeautifulSoup(resp.text, "lxml")

                message_texts = soup.select(".tgme_widget_message .tgme_widget_message_text")
                if not message_texts:
                    message_texts = soup.select(".tgme_widget_message_text")

                message_dates = soup.select(".tgme_widget_message .tgme_widget_message_date")
                match_count = len(message_texts)
                self.debug_info["selector_matches"] = match_count
                logger.info(
                    f"Telegram: {match_count} messages, "
                    f"{len(message_dates)} dates found"
                )

                for el in message_texts[:limit]:
                    text = el.get_text(separator=" ", strip=True)
                    if text and len(text) > 10:
                        items.append(text)

                if not items:
                    body = soup.get_text(separator="\n", strip=True)
                    lines = [l.strip() for l in body.split("\n") if len(l.strip()) > 15]
                    price_lines = [
                        l for l in lines
                        if re.search(r"(\d+[\.,]?\d*\s*(جنيه|ج\.م|EGP))", l)
                    ]
                    items = price_lines[:limit] if price_lines else lines[:limit]
                    logger.info(f"Fallback extraction: {len(items)} lines ({len(price_lines)} with prices)")

        except Exception as e:
            logger.error(f"Telegram scrape failed for {self.source.url}: {e}")
            raise

        return items
