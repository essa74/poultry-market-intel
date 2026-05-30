import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.api.deps import require_admin_token
from app.services.scrapers import seed_default_sources
from app.services.scrapers.registry import seed_sample_prices
from app.services.holiday_calendar_service import seed_holidays
from app.models.scraping import ScrapingSource

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    results = {"sources_count": 0, "holidays_count": 0, "sample_prices_count": 0}

    try:
        await seed_default_sources(db)
        r = await db.execute(select(func.count(ScrapingSource.id)))
        results["sources_count"] = r.scalar() or 0
        logger.info(f"Seed: {results['sources_count']} sources")
    except Exception:
        logger.exception("Seed failed for sources")
        raise

    try:
        results["holidays_count"] = await seed_holidays(db)
        logger.info(f"Seed: {results['holidays_count']} holidays")
    except Exception:
        logger.exception("Seed failed for holidays")
        raise

    try:
        results["sample_prices_count"] = await seed_sample_prices(db)
        logger.info(f"Seed: {results['sample_prices_count']} sample prices")
    except Exception:
        logger.exception("Seed failed for sample prices")
        raise

    await db.commit()

    return {
        **results,
        "message": "Seed completed",
    }
