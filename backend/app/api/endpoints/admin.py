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
    except Exception as e:
        logger.exception("Seed failed for sources")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Sources seed failed: {e}")

    try:
        r = await db.execute(select(func.count(ScrapingSource.id)))
        results["sources_count"] = r.scalar() or 0
    except Exception as e:
        logger.exception("Source count query failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Source count failed: {e}")

    try:
        results["holidays_count"] = await seed_holidays(db)
    except Exception as e:
        logger.exception("Seed failed for holidays")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Holiday seed failed: {e}")

    try:
        results["sample_prices_count"] = await seed_sample_prices(db)
    except Exception as e:
        logger.exception("Seed failed for sample prices")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Sample prices seed failed: {e}")

    return {
        **results,
        "message": "Seed completed",
    }
