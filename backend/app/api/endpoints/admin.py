import logging
import traceback
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
    try:
        print("Running seed_default_sources...")
        await seed_default_sources(db)

        r = await db.execute(select(func.count(ScrapingSource.id)))
        sources_count = r.scalar() or 0
        print(f"Running seed_holidays... (sources={sources_count})")
        holidays_count = await seed_holidays(db)

        print("Running seed_sample_prices...")
        sample_prices_count = await seed_sample_prices(db)

        print(f"Seed done: sources={sources_count} holidays={holidays_count} prices={sample_prices_count}")
        return {
            "success": True,
            "sources_count": sources_count,
            "holidays_count": holidays_count,
            "sample_prices_count": sample_prices_count,
            "message": "Seed completed",
        }

    except Exception as e:
        print(f"SEED ERROR: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.post("/fix-units")
async def fix_egg_units(db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    from app.models import PriceRecord
    from sqlalchemy import update

    try:
        stmt = (
            update(PriceRecord)
            .where(PriceRecord.product_type == "fertilized_eggs")
            .where(PriceRecord.unit == "per_tray")
            .values(unit="per_unit")
        )
        r = await db.execute(stmt)
        await db.commit()
        return {"success": True, "updated_records": r.rowcount, "message": "Units fixed"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        print(f"SEED ERROR: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
