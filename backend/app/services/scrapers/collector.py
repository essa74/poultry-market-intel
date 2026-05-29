"""
Collector — orchestrates scraping runs across all active sources.
Each source gets its OWN AsyncSession to prevent transaction conflicts.
"""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session
from app.models.scraping import ScrapingSource
from .registry import get_scraper, update_source_health

logger = logging.getLogger(__name__)

# Prevent overlapping scheduled runs
collection_lock = asyncio.Lock()


async def run_scheduled_collection(mode: str | None = None, db: AsyncSession = None):
    async with collection_lock:
        # Fetch active sources (only needs a brief session)
        if db is None:
            async with async_session() as session:
                sources = (await session.execute(
                    select(ScrapingSource).where(ScrapingSource.is_active == True)
                )).scalars().all()
        else:
            sources = (await db.execute(
                select(ScrapingSource).where(ScrapingSource.is_active == True)
            )).scalars().all()

        if not sources:
            logger.info("No active sources to scrape")
            return

        # Run sources SEQUENTIALLY — each gets its own session
        for s in sources:
            try:
                await _scrape_with_health(s)
            except Exception as e:
                logger.exception(f"Source [{s.name}] unexpectedly failed: {e}")

        logger.info(f"Collection complete: {len(sources)} sources processed")


async def _scrape_with_health(source: ScrapingSource) -> bool:
    """Scrape a single source with its own independent session."""
    sid = source.id
    sname = source.name

    # Each source gets a fresh session
    async with async_session() as db:
        scraper = get_scraper(source, db)
        if scraper is None:
            logger.warning(f"Source [{sname}]: no scraper registered, skipping")
            return False

        try:
            log = await scraper.run()
            if log:
                logger.info(
                    f"Source [{sname}]: collected={log.records_collected} "
                    f"dup={log.duplicates_skipped} invalid={log.invalid_skipped} "
                    f"status={log.status.value}"
                )
                if log.admin_warning:
                    logger.warning(f"Source [{sname}]: {log.admin_warning}")
        except Exception:
            logger.exception(f"Scrape for source {sid} failed")
            try:
                await db.rollback()
            except Exception:
                pass
            return False

        try:
            fresh = await update_source_health(sid, db)
            if fresh:
                logger.info(f"Source [{sname}]: health={fresh.health_score:.0f}%")
            else:
                logger.warning(f"Source [{sid}]: not found for health update")
        except Exception:
            logger.exception(f"Health update failed for source {sid}")
            try:
                await db.rollback()
            except Exception:
                pass

        return True


async def scrape_single_source(source_id: int, db: AsyncSession):
    """Used by endpoint: runs with endpoint's session (single-source only)."""
    source = (await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )).scalar_one_or_none()
    if not source:
        raise ValueError(f"Source id={source_id} not found")

    scraper = get_scraper(source, db)
    if scraper is None:
        logger.warning(f"Source [{source.name}]: no scraper registered")
        return False

    try:
        await scraper.run()
    except Exception:
        logger.exception(f"Scrape for source {source_id} failed")
        try:
            await db.rollback()
        except Exception:
            pass
        return False

    fresh = await update_source_health(source_id, db)
    return fresh is not None
