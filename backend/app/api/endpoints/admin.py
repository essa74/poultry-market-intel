import logging
import traceback
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from app.db.session import get_db, async_session
from app.api.deps import require_admin_token
from app.core.config import get_settings
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

        settings = get_settings()
        if settings.env == "production":
            print("Production mode — skipping sample prices")
            sample_prices_count = 0
        else:
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


@router.post("/delete-sample-prices")
async def delete_sample_prices(db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    from app.models import PriceRecord

    try:
        stmt = select(PriceRecord).where(
            or_(
                PriceRecord.source == "manual",
                PriceRecord.raw_post_text.contains("سعر تجريبي"),
            )
        )
        r = await db.execute(stmt)
        records = r.scalars().all()
        for rec in records:
            await db.delete(rec)
        await db.commit()
        return {"success": True, "deleted_count": len(records), "message": "Sample prices deleted"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@router.post("/reset-prices")
async def reset_prices(_=Depends(require_admin_token)):
    from app.models import PriceRecord
    from app.models.scraping import RawExtractedPrice

    try:
        async with async_session() as db:
            async with db.begin():
                rp = await db.execute(delete(RawExtractedPrice))
                deleted_raw = rp.rowcount or 0

                pp = await db.execute(delete(PriceRecord))
                deleted_prices = pp.rowcount or 0

        return {
            "success": True,
            "deleted_prices": deleted_prices,
            "deleted_raw": deleted_raw,
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
