"""
Base scraper class — all scrapers inherit from this.
"""
import abc
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Optional
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scraping import ScrapingSource, ScrapingLog, ScrapingJobStatus, RawExtractedPrice

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "scraping_snapshots"
)


class BaseScraper(abc.ABC):
    def __init__(self, source: ScrapingSource, db: AsyncSession):
        self.source = source
        self.source_id = source.id
        self.source_name = source.name
        self.source_url = source.url or ""
        self.source_config = source.config or {}
        self.db = db
        self.log: Optional[ScrapingLog] = None
        self.raw_content: str = ""
        self.debug_info: dict = {}
        logger.info("BaseScraper init: source=%s config=%s", source.id, source.config)

    @abc.abstractmethod
    async def fetch_raw_data(self) -> list:
        """Fetch raw text/listings from the source. May contain strings or structured dicts."""

    async def run(self) -> ScrapingLog:
        source_id = self.source_id
        source_name = self.source_name
        start = datetime.utcnow()
        self.log = ScrapingLog(
            source_id=source_id,
            status=ScrapingJobStatus.RUNNING,
            job_id=f"{source_id}-{start.strftime('%Y%m%d%H%M%S')}",
        )
        self.db.add(self.log)
        await self.db.commit()
        await self.db.refresh(self.log)

        raw_items = []
        try:
            raw_items = await self.fetch_raw_data()

            raw_length = len(self.raw_content) if self.raw_content else 0
            self.log.raw_content_length = raw_length
            self.log.fetched_text = (self.raw_content[:1000]) if self.raw_content else None
            self.log.selector_matches = self.debug_info.get("selector_matches", 0)

            logger.info(
                f"Source [{source_name}]: fetched {raw_length} bytes, "
                f"{len(raw_items)} raw items, "
                f"selector_matches={self.debug_info.get('selector_matches', 'N/A')}"
            )

            if not raw_items:
                config = self.source_config
                content_type = config.get("type", "")
                is_mahdy = content_type == "mahdy" or "mahdy" in self.source_url.lower()
                is_facebook_blocked = self.debug_info.get("facebook_blocked", False)
                is_image_only = self.debug_info.get("image_only_detected", False)
                if is_mahdy:
                    self.log.status = ScrapingJobStatus.PARTIAL
                    self.log.admin_warning = "مصدر المهدي لا ينشر أسعارًا عامة على الموقع — البيانات قد تكون متاحة عبر واتساب فقط"
                    logger.info(f"Source [{source_name}]: mahdy info source, setting partial")
                elif is_facebook_blocked:
                    self.log.status = ScrapingJobStatus.PARTIAL
                    self.log.admin_warning = "تعذر قراءة الصفحة العامة من فيسبوك — استخدم الإدخال اليدوي أو رابط منشور مباشر"
                    logger.warning(f"Source [{source_name}]: facebook blocked")
                elif is_image_only:
                    self.log.status = ScrapingJobStatus.PARTIAL
                    self.log.admin_warning = "الأسعار منشورة داخل صورة ولا يمكن قراءتها نصيًا حاليًا"
                    logger.warning(f"Source [{source_name}]: image-only prices detected")
                else:
                    self.log.status = ScrapingJobStatus.FAILED
                self.log.records_collected = 0
                logger.warning(f"Source [{source_name}]: no raw items fetched")
            else:
                await self._process_items(raw_items)
        except Exception:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(f"Scraper {source_id} failed")
            if self.log is not None:
                self.log.status = ScrapingJobStatus.FAILED
                self.log.error_traceback = traceback.format_exc()
                exc = sys.exc_info()[1]
                if exc:
                    self.log.error_type = type(exc).__name__
                    self.log.error_message = str(exc)
                self.db.add(self.log)
                if self.raw_content:
                    self.log.html_snapshot_path = self._save_snapshot(self.raw_content)

        end = datetime.utcnow()
        self.log.finished_at = end
        self.log.duration_seconds = (end - start).total_seconds()
        await self.db.commit()
        await self.db.refresh(self.log)
        return self.log

    def _save_snapshot(self, content: str) -> str:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"source_{self.source_id}_{ts}.html"
        path = os.path.join(SNAPSHOT_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Snapshot saved: {path}")
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
        return path

    async def _process_items(self, items: list):
        from .price_normalizer import normalizer, is_poultry_relevant, contains_large_money
        from .ai_extractor import ai_extractor
        from .config import get_scraper_settings
        from .price_persistence import save_extracted_price

        settings = get_scraper_settings()
        collected = 0
        skipped = 0
        seen = 0
        non_poultry_count = 0
        valid_saved = 0
        duplicates_skipped = 0
        invalid_skipped = 0
        structured_saved = 0

        logger.info(
            f"Source [{self.source_name}]: processing {len(items)} items "
            f"(parsed_price_lines={self.debug_info.get('parsed_price_lines_count', 'N/A')})"
        )

        for raw_item in items:
            # ── Handle structured dict items (bypass normalizer) ───────
            if isinstance(raw_item, dict):
                seen += 1
                logger.debug(f"Structured dict [{seen}]: {raw_item.get('raw_text', '')[:120]}")
                saved = await self._save_structured_price(raw_item)
                if saved:
                    collected += 1
                    valid_saved += 1
                    structured_saved += 1
                else:
                    skipped += 1
                    invalid_skipped += 1
                continue

            raw_text = raw_item
            if not raw_text or not raw_text.strip():
                continue

            # Safety: reject full-post strings (>500 chars with multi-line content)
            # that contain multiple price lines — these bypass the structured parser
            if isinstance(raw_text, str) and len(raw_text) > 500:
                newline_count = raw_text.count("\n")
                if newline_count >= 5 or any(kw in raw_text for kw in ["بورصه", "بورصة"]):
                    skipped += 1
                    invalid_skipped += 1
                    raw = RawExtractedPrice(
                        source_id=self.source_id,
                        log_id=self.log.id,
                        raw_text=raw_text[:2000],
                        extraction_method="regex",
                        is_normalized=False,
                        confidence=0.0,
                        is_failed_sample=True,
                    )
                    self.db.add(raw)
                    await self.db.flush()
                    logger.warning(
                        f"Rejected full-post string [{seen}]: {len(raw_text)} chars, "
                        f"{newline_count} newlines — looks like full post, not single line"
                    )
                    self.log.admin_warning = (
                        "تم رفض نص كامل للمنشور (أكثر من 500 حرف) — "
                        "يجب تحليل النص عبر الروابط المباشرة فقط"
                    )
                    continue

            seen += 1
            logger.debug(f"Raw text [{seen}]: {raw_text[:200]}")

            if contains_large_money(raw_text):
                non_poultry_count += 1
                skipped += 1
                invalid_skipped += 1
                raw = RawExtractedPrice(
                    source_id=self.source_id,
                    log_id=self.log.id,
                    raw_text=raw_text[:2000],
                    extraction_method="regex",
                    is_normalized=False,
                    confidence=0.0,
                    is_failed_sample=True,
                )
                self.db.add(raw)
                await self.db.flush()
                logger.debug(f"Large money item skipped [{seen}]")
                continue

            if not is_poultry_relevant(raw_text):
                non_poultry_count += 1
                skipped += 1
                invalid_skipped += 1
                raw = RawExtractedPrice(
                    source_id=self.source_id,
                    log_id=self.log.id,
                    raw_text=raw_text[:2000],
                    extraction_method="regex",
                    is_normalized=False,
                    confidence=0.0,
                    is_failed_sample=True,
                )
                self.db.add(raw)
                await self.db.flush()
                logger.debug(f"Non-poultry item skipped [{seen}]: no poultry terms found")
                continue

            result = ai_extractor.extract(raw_text) if settings.ai_extraction_enabled else normalizer.normalize(raw_text)

            if result is None:
                extraction_method = "regex"
                confidence = 0.0
                is_valid = False
            else:
                extraction_method = "ai" if (settings.ai_extraction_enabled and result.confidence > 0.5) else "regex"
                confidence = result.confidence
                is_valid = result.is_valid()

            is_failed_sample = not is_valid

            raw = RawExtractedPrice(
                source_id=self.source_id,
                log_id=self.log.id,
                raw_text=raw_text[:2000],
                extraction_method=extraction_method,
                is_normalized=is_valid,
                confidence=confidence,
                is_failed_sample=is_failed_sample,
            )

            if result and is_valid:
                raw.product_type = result.product_type
                raw.category = result.category
                raw.price = result.price
                raw.currency = result.currency
                raw.unit = result.unit
                raw.region = result.region
                raw.recorded_date = result.recorded_date
                if hasattr(result, 'product_group'):
                    raw.product_group = result.product_group

                self.db.add(raw)
                await self.db.flush()

                action, record = await save_extracted_price(
                    self.db, SimpleNamespace(name=self.source_name), self.log, raw
                )
                if action == "saved":
                    collected += 1
                    valid_saved += 1
                    logger.debug(f"Price saved: {raw.product_type} @ {raw.price}")
                elif action == "duplicate":
                    skipped += 1
                    duplicates_skipped += 1
                    logger.debug(f"Duplicate skipped: {raw.product_type}/{raw.price}")
                else:
                    skipped += 1
                    invalid_skipped += 1
                    logger.debug(f"Invalid: confidence={raw.confidence:.2f}")
            else:
                skipped += 1
                invalid_skipped += 1
                self.db.add(raw)
                logger.debug(f"No match or invalid: confidence={confidence:.2f}")

            await self.db.flush()

        self.log.records_collected = collected
        self.log.records_skipped = skipped
        self.log.valid_saved = valid_saved
        self.log.duplicates_skipped = duplicates_skipped
        self.log.invalid_skipped = invalid_skipped
        self.log.status = ScrapingJobStatus.SUCCESS if collected > 0 else (
            ScrapingJobStatus.PARTIAL if skipped > 0 else ScrapingJobStatus.FAILED
        )

        if seen > 0 and non_poultry_count == seen and structured_saved == 0:
            config = self.source_config
            content_type = config.get("type", "")
            is_mahdy = content_type == "mahdy" or "mahdy" in self.source_url.lower()
            if is_mahdy:
                self.log.admin_warning = "مصدر المهدي لا ينشر أسعارًا عامة على الموقع — البيانات قد تكون متاحة عبر واتساب فقط"
            elif not structured_saved:
                self.log.admin_warning = "هذا المصدر لا يحتوي على أسعار دواجن"
            logger.warning(f"Source [{self.source_name}]: {self.log.admin_warning}")

        logger.info(
            f"Source [{self.source_name}]: "
            f"{seen} seen, {collected} inserted ({structured_saved} structured), {skipped} skipped, "
            f"saved={valid_saved} dup={duplicates_skipped} invalid={invalid_skipped} "
            f"(status={self.log.status.value})"
        )

    async def _save_structured_price(self, item: dict) -> bool:
        from .price_persistence import save_extracted_price

        raw_text = item.get("raw_text") or item.get("normalized_line", "")
        product_type = item.get("product_type")
        category = item.get("category")
        price = item.get("price")
        unit = item.get("unit", "per_unit")
        product_group = item.get("product_group", "fertilized_eggs")
        confidence = item.get("confidence", 0.8)
        detected_date_str = item.get("detected_date")

        if not product_type or not category or price is None:
            logger.warning(f"Structured item missing required fields: {item}")
            return False

        logger.info(
            f"Structured save: {product_type}/{category} @ {price} {unit} "
            f"(conf={confidence}) — \"{raw_text[:80]}\""
        )

        recorded_date = None
        if detected_date_str:
            try:
                recorded_date = datetime.strptime(detected_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        raw = RawExtractedPrice(
            source_id=self.source_id,
            log_id=self.log.id,
            raw_text=raw_text[:500],
            extraction_method="regex",
            is_normalized=True,
            confidence=confidence,
            product_type=product_type,
            category=category,
            price=price,
            unit=unit,
            product_group=product_group,
            recorded_date=recorded_date,
        )
        self.db.add(raw)
        await self.db.flush()

        # Pass the full Facebook post text as raw_post_text
        raw_post_text = self.debug_info.get("direct_post_text")

        action, record = await save_extracted_price(
            self.db, SimpleNamespace(name=self.source_name), self.log, raw,
            raw_post_text=raw_post_text,
        )
        if action == "saved":
            logger.info(f"Structured price saved: {product_type}/{category} @ {price}")
            return True
        elif action == "duplicate":
            logger.debug(f"Structured price duplicate: {product_type}/{category} @ {price}")
            return False
        else:
            logger.debug(f"Structured price invalid: {product_type}/{category} @ {price}")
            return False
