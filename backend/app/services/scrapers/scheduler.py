"""
APScheduler integration — runs collection:
  - Morning & evening for all active sources
  - Every 3 hours for Facebook sources with auto_discover=true
Uses asyncio.Lock to prevent overlapping runs.
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from .collector import run_scheduled_collection, collection_lock, _scrape_with_health
from .config import get_scraper_settings
from app.db.session import async_session
from app.models.scraping import ScrapingSource
from app.services.news_scraper import refresh_all_news

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def morning_job():
    if collection_lock.locked():
        logger.warning("Collection already running, skipping morning job")
        return
    logger.info("=== Morning collection job started ===")
    await run_scheduled_collection("morning")


async def evening_job():
    if collection_lock.locked():
        logger.warning("Collection already running, skipping evening job")
        return
    logger.info("=== Evening collection job started ===")
    await run_scheduled_collection("evening")


async def facebook_auto_discover_job():
    """Runs every 3 hours — only Facebook sources with auto_discover enabled."""
    if collection_lock.locked():
        logger.info("Collection lock held, skipping facebook auto-discover job")
        return

    async with collection_lock:
        async with async_session() as db:
            sources = (await db.execute(
                select(ScrapingSource).where(
                    ScrapingSource.is_active == True,
                    ScrapingSource.source_type == "facebook",
                )
            )).scalars().all()

        fb_sources = [
            s for s in sources
            if (s.config or {}).get("auto_discover", True) is not False
        ]

        if not fb_sources:
            logger.info("Facebook auto-discover: no eligible sources found")
            return

        logger.info(f"=== Facebook auto-discover job: {len(fb_sources)} sources ===")

        for s in fb_sources:
            try:
                await _scrape_with_health(s)
            except Exception as e:
                logger.exception(f"Facebook auto-discover source [{s.name}] failed: {e}")

        logger.info(f"Facebook auto-discover job completed ({len(fb_sources)} sources)")


async def news_refresh_job():
    logger.info("=== News refresh job started ===")
    try:
        async with async_session() as db:
            result = await refresh_all_news(db)
            logger.info(f"News refresh: {result['inserted']} new, {result['duplicates_skipped']} duplicates, {result['deleted_low_relevance']} cleaned")
    except Exception as e:
        logger.warning(f"News refresh failed: {e}")


def start_scheduler():
    settings = get_scraper_settings()

    scheduler.add_job(
        morning_job,
        CronTrigger(hour=settings.morning_hour, minute=0),
        id="morning_collection",
        name="Morning price collection",
        replace_existing=True,
    )

    scheduler.add_job(
        evening_job,
        CronTrigger(hour=settings.evening_hour, minute=0),
        id="evening_collection",
        name="Evening price collection",
        replace_existing=True,
    )

    scheduler.add_job(
        facebook_auto_discover_job,
        IntervalTrigger(hours=3),
        id="facebook_auto_discover",
        name="Facebook auto-discover every 3h",
        replace_existing=True,
    )

    scheduler.add_job(
        news_refresh_job,
        IntervalTrigger(hours=6),
        id="news_refresh",
        name="News refresh every 6 hours",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: morning={settings.morning_hour}:00, "
        f"evening={settings.evening_hour}:00, "
        f"facebook every 3h, news every 6h"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
