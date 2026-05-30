"""
Scraper registry — maps source types to scraper classes, manages source health.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scraping import ScrapingSource, ScrapingSourceType, ScrapingJobStatus, ScrapingLog
from .base import BaseScraper
from .config import get_scraper_settings, DEFAULT_SOURCES
from .playwright_scraper import PlaywrightWebScraper
from .telegram_scraper import TelegramChannelScraper
from .facebook_scraper import FacebookPageScraper

logger = logging.getLogger(__name__)

SCRAPER_MAP = {}

def register_scraper(source_type: ScrapingSourceType, scraper_cls: type[BaseScraper]):
    SCRAPER_MAP[source_type] = scraper_cls
    logger.info(f"Registered scraper for {source_type}: {scraper_cls.__name__}")

register_scraper(ScrapingSourceType.WEBSITE, PlaywrightWebScraper)
register_scraper(ScrapingSourceType.TELEGRAM, TelegramChannelScraper)
register_scraper(ScrapingSourceType.FACEBOOK, FacebookPageScraper)


def get_scraper(source: ScrapingSource, db: AsyncSession) -> Optional[BaseScraper]:
    cls = SCRAPER_MAP.get(source.source_type)
    if not cls:
        logger.error(f"No scraper registered for source type: {source.source_type}")
        return None
    return cls(source, db)


async def seed_default_sources(db: AsyncSession):
    for src_data in DEFAULT_SOURCES:
        data = dict(src_data)
        active = data.pop("is_active", True)
        stmt = select(ScrapingSource).where(ScrapingSource.url == data["url"])
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is None:
            source = ScrapingSource(**data, is_active=active)
            db.add(source)
            logger.info(
                f"Seeded scraping source: {data['name']} "
                f"(active={active})"
            )
        else:
            if existing.is_active != active:
                existing.is_active = active
                logger.info(
                    f"Updated source '{data['name']}' active={active}"
                )

    await db.commit()

    rows = (await db.execute(
        select(ScrapingSource).order_by(ScrapingSource.id)
    )).scalars().all()

    urls_seen = {}
    for row in rows:
        if row.url in urls_seen:
            await db.delete(row)
            logger.info(f"Removed duplicate source id={row.id} url={row.url}")
        else:
            urls_seen[row.url] = row.id

    await db.commit()


async def update_source_health(source_id: int, db: AsyncSession) -> ScrapingSource | None:
    source = (await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )).scalar_one_or_none()
    if not source:
        return None

    settings = get_scraper_settings()
    logs_stmt = (
        select(ScrapingLog)
        .where(ScrapingLog.source_id == source_id)
        .order_by(ScrapingLog.started_at.desc())
        .limit(10)
    )
    logs = (await db.execute(logs_stmt)).scalars().all()

    if not logs:
        source.health_score = 100.0
        source.consecutive_failures = 0
    else:
        valid_collects = sum(
            1 for l in logs
            if l.status in (ScrapingJobStatus.SUCCESS, ScrapingJobStatus.PARTIAL)
            and l.records_collected is not None
            and l.records_collected > 0
        )
        source.health_score = (valid_collects / len(logs)) * 100

        source.consecutive_failures = sum(
            1 for l in logs
            if l.status == ScrapingJobStatus.FAILED
            or (l.status == ScrapingJobStatus.PARTIAL and (l.records_collected is None or l.records_collected == 0))
        )

    latest = logs[0] if logs else None
    if latest:
        if latest.status in (ScrapingJobStatus.SUCCESS, ScrapingJobStatus.PARTIAL) and (latest.records_collected or 0) > 0:
            source.last_success_at = latest.finished_at
        elif latest.status == ScrapingJobStatus.FAILED or (latest.records_collected or 0) == 0:
            source.last_failure_at = latest.finished_at

    await db.commit()
    return source


async def seed_sample_prices(db: AsyncSession) -> int:
    """Generate 3 days of sample price records if the prices table is empty."""
    from app.models import PriceRecord
    from sqlalchemy import select, func
    from datetime import date, timedelta

    result = await db.execute(select(func.count(PriceRecord.id)))
    total = result.scalar() or 0
    if total > 0:
        logger.info(f"seed_sample_prices: table already has {total} rows — skipping")
        return 0

    logger.info("seed_sample_prices: generating 3 days of sample data...")

    FEATURED_CATEGORIES = [
        ("white", "أبيض", 4.2),
        ("sasso", "ساسو", 4.8),
        ("baladi", "بلدي", 5.5),
        ("local", "محلي / فيومي وجميزة", 4.5),
        ("duck", "بط", 6.0),
        ("quail", "سمان", 3.5),
        ("turkey", "رومي", 8.0),
        ("ostrich", "نعام", 35.0),
    ]
    today = date.today()
    count = 0
    for day_offset in range(3):
        d = today - timedelta(days=day_offset)
        for cat_key, cat_label, base_price in FEATURED_CATEGORIES:
            variation = (day_offset * 1.5) + (hash(cat_key + str(d)) % 10 - 5) * 0.5
            record = PriceRecord(
                product_type="fertilized_eggs",
                category=cat_key,
                price=round(base_price + variation, 1),
                currency="EGP",
                unit="per_unit",
                source="بورصة المهدي جروب",
                recorded_date=d,
                raw_product_name=f"بيض مخصب {cat_label}",
                product_group="fertilized_eggs",
            )
            db.add(record)
            count += 1

    chick_data = [
        ("white", "أبيض", 18.0),
        ("sasso", "ساسو", 15.5),
        ("baladi", "بلدي", 12.0),
    ]
    for day_offset in range(3):
        d = today - timedelta(days=day_offset)
        for cat_key, cat_label, base_price in chick_data:
            variation = (day_offset * 0.3) + (hash(f"chick_{cat_key}{d}") % 10 - 5) * 0.2
            record = PriceRecord(
                product_type="day_old_chicks",
                category=cat_key,
                price=round(base_price + variation, 1),
                currency="EGP",
                unit="per_unit",
                source="بورصة المهدي جروب",
                recorded_date=d,
                raw_product_name=f"كتاكيت {cat_label}",
                product_group="chicks",
            )
            db.add(record)
            count += 1

    await db.commit()
    logger.info(f"seed_sample_prices: generated {count} records")
    return count


async def get_active_sources(db: AsyncSession) -> list[ScrapingSource]:
    stmt = select(ScrapingSource).where(
        ScrapingSource.is_active == True
    )
    return (await db.execute(stmt)).scalars().all()


async def get_failed_sources_for_retry(db: AsyncSession) -> list[ScrapingSource]:
    settings = get_scraper_settings()
    stmt = select(ScrapingSource).where(
        ScrapingSource.is_active == True,
        ScrapingSource.consecutive_failures > 0,
        ScrapingSource.consecutive_failures <= settings.max_retries,
    ).order_by(ScrapingSource.last_failure_at.desc().nullslast())
    return (await db.execute(stmt)).scalars().all()
