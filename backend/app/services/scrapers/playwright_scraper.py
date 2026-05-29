"""
Website scraper using Playwright + BeautifulSoup.
Extracts prices from HTML tables, price cards, and news ticker layouts.
"""
import logging
import os
import re
from datetime import datetime
from typing import Optional
import feedparser
import httpx
from bs4 import BeautifulSoup, Tag
from .base import BaseScraper, SNAPSHOT_DIR
from .config import get_scraper_settings

logger = logging.getLogger(__name__)

PRICE_KEYWORDS = [
    "جنيه", "جنية", "ج.م", "EGP", "قرش",
    "بيض", "كتاكيت", "كتكوت", "دواجن",
    "أبيض", "ابيض", "بلدي", "ساسو",
    "عمر يوم", "للألف", "لل 1000",
]

PRODUCT_KEYWORDS_SET = [
    "بيض مخصب", "بيض", "كتاكيت", "كتكوت",
    "دواجن", "فراخ", "بطة", "وز",
]

SETRO_SECTIONS = [
    "البيض", "كتاكيت", "كتكوت", "أعلاف", "علف",
    "دواجن", "أسعار", "طبق", "كرتونة",
]

MAHDY_TARGET_KEYWORDS = [
    "كتاكيت", "كتكوت", "بيض مخصب", "بيض تفريخ",
    "أعلاف", "ذرة", "صويا", "بورصة",
    "الفراخ", "الأمهات", "المفرخات", "التسمين",
    "الشركات", "الإنتاج", "تكلفة", "سعر",
    "الدواجن", "البيض", "أسعار",
]

MAHDY_API_URLS = [
    "https://mahdy-group.com/wp-json/wp/v2/at_biz_dir?per_page=50",
    "https://mahdy-group.com/wp-json/wp/v2/posts?per_page=20",
    "https://mahdy-group.com/feed/",
]


class PlaywrightWebScraper(BaseScraper):
    async def _block_unnecessary(self, route):
        resource_type = route.request.resource_type
        if resource_type in ("image", "font", "media"):
            await route.abort()
        else:
            await route.continue_()

    async def fetch_raw_data(self) -> list[str]:
        items = []
        page = None
        playwright = None
        try:
            from playwright.async_api import async_playwright

            settings = get_scraper_settings()
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=settings.playwright_headless,
            )
            page = await browser.new_page(
                viewport={"width": 1280, "height": 900}
            )

            await page.route("**/*", self._block_unnecessary)

            await page.goto(self.source.url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector("body", timeout=15000)

            html = await page.content()
            self.raw_content = html
            logger.info(f"Fetched {self.source.url}: {len(html)} bytes")

            try:
                os.makedirs(SNAPSHOT_DIR, exist_ok=True)
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(
                    SNAPSHOT_DIR, f"screenshot_{self.source.id}_{ts}.png"
                )
                await page.screenshot(path=screenshot_path, full_page=True)
                self.debug_info["screenshot_path"] = screenshot_path
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")

            config = self.source.config or {}
            content_type = config.get("type", "auto")

            soup = BeautifulSoup(html, "lxml")

            if content_type == "mahdy":
                items = self._parse_mahdy(soup)
            elif content_type == "setro":
                items = self._parse_setro(soup, config)
            elif content_type == "table":
                items = self._parse_tables(soup)
            elif content_type == "card":
                items = self._parse_cards(soup, config)
            elif content_type == "ticker":
                items = self._parse_ticker(soup)
            else:
                items = self._parse_auto(soup, config)

            self.debug_info["selector_matches"] = len(items)
            logger.info(f"Extracted {len(items)} items using {content_type} parser")

        except Exception as e:
            logger.error(f"Playwright scrape failed for {self.source.url}: {e}")
            raise
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

        return items

    def _parse_setro(self, soup: BeautifulSoup, config: dict) -> list[str]:
        items = []

        section_selectors = config.get("selectors", [])
        if not section_selectors:
            section_selectors = [
                ".price-table", ".prices-table", "table",
                ".section", ".product-item", ".price-item",
                "[class*=price]", "[class*=table]",
                ".card", ".box",
            ]

        sections = []
        for sel in section_selectors:
            matched = soup.select(sel)
            if matched:
                sections.extend(matched)

        if not sections:
            for keyword in SETRO_SECTIONS:
                for tag in ("div", "section", "table", "ul"):
                    found = soup.find_all(tag, string=re.compile(keyword, re.I))
                    for el in found:
                        parent = el.find_parent(["div", "section", "table"])
                        if parent and parent not in sections:
                            sections.append(parent)

        seen = set()
        for sec in sections:
            text = sec.get_text(separator=" ", strip=True)
            if not text or text in seen:
                continue
            seen.add(text)

            if any(kw in text for kw in PRICE_KEYWORDS) and re.search(r"\d+", text):
                items.append(text)
                continue

            rows = sec.select("tr") if sec.name == "table" else []
            if rows:
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    row_text = " | ".join(c.get_text(separator=" ", strip=True) for c in cells)
                    if row_text and any(kw in row_text for kw in PRICE_KEYWORDS) and re.search(r"\d+", row_text):
                        if row_text not in items:
                            items.append(row_text)

        table_fallbacks = soup.select("table")
        for t in table_fallbacks:
            text = t.get_text(separator=" | ", strip=True)
            if text and any(kw in text for kw in PRICE_KEYWORDS) and re.search(r"\d+", text):
                if text not in items:
                    items.append(text)

        body_text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in body_text.split("\n") if len(l.strip()) > 10]
        price_lines = [l for l in lines if any(kw in l for kw in PRICE_KEYWORDS) and re.search(r"\d+", l)]
        for line in price_lines:
            if line not in items:
                items.append(line)

        # Remove large composite texts (section headers with all prices aggregated)
        items = [i for i in items if len(i) < 150]
        logger.info(f"Setro parser: {len(items)} items (after removing composites)")
        return items

    def _parse_mahdy(self, soup: BeautifulSoup) -> list[str]:
        items = []
        candidates = []
        rejected = []

        # Strategy 1: scan visible content elements (articles, posts, entries, main content)
        content_selectors = [
            "article", ".post", ".hentry", ".entry-content", ".site-content",
            "main", ".content-area", "#content", ".post-content",
            ".listing-content", ".directorist-listing-content",
            ".atbd_content", ".atbdp_content",
            "[class*=price]", "[class*=pricing]",
            "table", ".price-table",
        ]
        found_blocks = []
        for sel in content_selectors:
            matched = soup.select(sel)
            for el in matched:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 20 and text not in found_blocks:
                    found_blocks.append(text)

        self.debug_info["mahdy_blocks_found"] = len(found_blocks)
        self.debug_info["mahdy_content_selectors"] = content_selectors

        for block_text in found_blocks:
            has_target = any(kw in block_text for kw in MAHDY_TARGET_KEYWORDS)
            has_currency = bool(re.search(r"(جنيه|ج\.م|EGP|جم|قرش)", block_text))
            has_number = bool(re.search(r"\d+", block_text))
            if has_target and has_number and has_currency:
                candidates.append(block_text[:2000])
            elif has_target and has_number:
                candidates.append(block_text[:2000])
            else:
                rejected.append(block_text[:200])

        self.debug_info["mahdy_candidate_blocks"] = len(candidates)

        # Strategy 2: scan all page text in targeted paragraph chunks
        for el in soup.find_all(["p", "li", "span", "div", "h1", "h2", "h3", "h4"]):
            text = el.get_text(separator=" ", strip=True)
            if len(text) < 15:
                continue
            has_target = any(kw in text for kw in MAHDY_TARGET_KEYWORDS)
            has_number = bool(re.search(r"\d+", text))
            has_currency = bool(re.search(r"(جنيه|ج\.م|EGP|جم|قرش)", text))
            if has_target and has_number:
                if text not in candidates:
                    candidates.append(text[:2000])

        self.debug_info["mahdy_candidates_total"] = len(candidates)

        # Strategy 3: try REST API endpoints for listings
        import httpx
        api_items = []
        for api_url in MAHDY_API_URLS:
            try:
                resp = httpx.get(api_url, timeout=10.0, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    if api_url.endswith("feed/"):
                        feed = feedparser.parse(resp.text)
                        for entry in feed.entries[:20]:
                            title = entry.get("title", "")
                            summary = re.sub(r"<[^>]+>", "", entry.get("summary", "") or "")
                            combined = f"{title} {summary}"
                            has_target = any(kw in combined for kw in MAHDY_TARGET_KEYWORDS)
                            has_number = bool(re.search(r"\d+", combined))
                            if has_target and has_number:
                                api_items.append(combined[:2000])
                    else:
                        data = resp.json()
                        if isinstance(data, list):
                            for item in data[:30]:
                                title = item.get("title", {}).get("rendered", "") if isinstance(item.get("title"), dict) else str(item.get("title", ""))
                                content = item.get("content", {}).get("rendered", "") if isinstance(item.get("content"), dict) else str(item.get("content", ""))
                                excerpt = item.get("excerpt", {}).get("rendered", "") if isinstance(item.get("excerpt"), dict) else ""
                                combined = f"{title} {content} {excerpt}"
                                has_target = any(kw in combined for kw in MAHDY_TARGET_KEYWORDS)
                                has_number = bool(re.search(r"\d+", combined))
                                has_currency = bool(re.search(r"(جنيه|ج\.م|EGP|جم|قرش)", combined))
                                if has_target and has_number:
                                    snippet = f"{title}: {content[:500]}"
                                    api_items.append(snippet[:2000])
            except Exception as e:
                logger.debug(f"Mahdy API fetch failed for {api_url}: {e}")

        self.debug_info["mahdy_api_items"] = len(api_items)

        # Combine candidates and api_items, deduplicate
        all_texts = candidates + api_items
        seen = set()
        for t in all_texts:
            if t not in seen:
                seen.add(t)
                items.append(t)

        items = items[:50]

        # Record samples of what was rejected
        self.debug_info["mahdy_rejected_samples"] = rejected[:10]

        logger.info(
            f"Mahdy parser: {len(items)} items "
            f"(blocks={len(found_blocks)}, api={len(api_items)}, rejected={len(rejected)})"
        )
        return items

    def _parse_tables(self, soup: BeautifulSoup) -> list[str]:
        items = []
        tables = soup.select("table")
        logger.info(f"Found {len(tables)} HTML tables")

        for table in tables:
            rows = table.select("tr")
            headers = [th.get_text(strip=True).lower() for th in rows[0].select("th, td")] if rows else []

            for row in rows[1:]:
                cells = row.select("td, th")
                if not cells:
                    continue

                row_text = " | ".join(c.get_text(separator=" ", strip=True) for c in cells)
                if any(kw in row_text for kw in PRICE_KEYWORDS):
                    items.append(row_text)
                    continue

                if any(re.search(r"\d+[\.,]?\d*", c.get_text(strip=True)) for c in cells):
                    if any(re.search(r"[أ-يa-zA-Z]", c.get_text(strip=True)) for c in cells):
                        items.append(row_text)

        if not items:
            fallback = soup.select("table")
            for t in fallback:
                text = t.get_text(separator=" | ", strip=True)
                if text and any(kw in text for kw in PRICE_KEYWORDS):
                    items.append(text)

        logger.info(f"Table parser: {len(items)} items")
        return items

    def _parse_cards(self, soup: BeautifulSoup, config: dict) -> list[str]:
        items = []
        selector = config.get("selector", "[class*=price], [class*=card], [class*=item]")
        cards = soup.select(selector)
        logger.info(f"Card selector matched {len(cards)} elements")

        for card in cards:
            text = card.get_text(separator=" ", strip=True)
            if any(kw in text for kw in PRICE_KEYWORDS) and re.search(r"\d+", text):
                items.append(text)

        if not items:
            candidates = soup.find_all(["div", "article", "section", "li"],
                                       class_=re.compile(r"price|card|item|product|box", re.I))
            for c in candidates:
                text = c.get_text(separator=" ", strip=True)
                if len(text) > 10 and any(kw in text for kw in PRICE_KEYWORDS):
                    items.append(text)

        logger.info(f"Card parser: {len(items)} items")
        return items

    def _parse_ticker(self, soup: BeautifulSoup) -> list[str]:
        items = []
        tickers = soup.select("marquee, [class*=ticker], [class*=marquee], [class*=scroll]")
        logger.info(f"Found {len(tickers)} ticker elements")

        for t in tickers:
            text = t.get_text(separator=" ", strip=True)
            if text and any(kw in text for kw in PRICE_KEYWORDS):
                items.append(text)

        body = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in body.split("\n") if len(l.strip()) > 15]
        price_lines = [l for l in lines if any(kw in l for kw in PRICE_KEYWORDS)]

        for line in price_lines:
            if line not in items:
                items.append(line)

        logger.info(f"Ticker parser: {len(items)} items")
        return items[:30]

    def _parse_auto(self, soup: BeautifulSoup, config: dict) -> list[str]:
        items = []

        items.extend(self._parse_tables(soup))

        if not items:
            selector = config.get("selector", "body")
            elements = soup.select(selector)
            match_count = len(elements)
            self.debug_info["selector_matches"] = match_count
            logger.info(f"Auto selector '{selector}' matched {match_count} elements")

            for el in elements:
                text = el.get_text(separator=" ", strip=True)
                if any(kw in text for kw in PRICE_KEYWORDS) and re.search(r"\d+", text):
                    items.append(text)

        if not items:
            items.extend(self._parse_cards(soup, config))

        if not items:
            items.extend(self._parse_ticker(soup))

        if not items:
            body_text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in body_text.split("\n") if len(l) > 10]
            price_lines = [l for l in lines if any(kw in l for kw in PRICE_KEYWORDS)]
            items = price_lines[:20] if price_lines else lines[:20]
            logger.info(f"Auto fallback: {len(items)} lines ({len(price_lines)} with price keywords)")

        return items
