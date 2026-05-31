import logging
import traceback
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
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


@router.post("/delete-all-prices")
async def delete_all_prices(_=Depends(require_admin_token)):
    from app.models import PriceRecord
    from app.models.scraping import RawExtractedPrice

    try:
        async with async_session() as db:
            async with db.begin():
                rp = await db.execute(delete(RawExtractedPrice))
                deleted_raw = rp.rowcount or 0

                pp = await db.execute(delete(PriceRecord))
                deleted_prices = pp.rowcount or 0

        logger.info(f"delete-all-prices: {deleted_prices} price_records, {deleted_raw} raw_extracted_prices deleted")
        return {
            "success": True,
            "deleted_price_records": deleted_prices,
            "deleted_raw_records": deleted_raw,
            "message": "All prices deleted",
        }
    except Exception as e:
        logger.error(f"delete-all-prices failed: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


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


class ManualPriceEntry(BaseModel):
    product_type: str = Field(default="fertilized_eggs", pattern=r"^(fertilized_eggs|day_old_chicks)$")
    category: str = Field(..., pattern=r"^(white|sasso|baladi|local|duck|quail|turkey|ostrich)$")
    raw_product_name: str = ""
    price: float = Field(..., gt=0)
    unit: str = Field(default="per_unit", pattern=r"^(per_unit|per_tray|per_ton)$")
    source: str = "يدوي"
    recorded_date: Optional[date] = None
    notes: Optional[str] = None


@router.post("/prices/manual")
async def create_manual_price(entry: ManualPriceEntry, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    from app.models import PriceRecord

    try:
        record_date = entry.recorded_date or date.today()
        unit = entry.unit
        if entry.product_type == "fertilized_eggs" and unit == "per_tray":
            unit = "per_unit"
        product_group = "fertilized_eggs" if entry.product_type == "fertilized_eggs" else "chicks"

        record = PriceRecord(
            product_type=entry.product_type,
            category=entry.category,
            price=entry.price,
            currency="EGP",
            unit=unit,
            market="manual",
            source=entry.source or "يدوي",
            raw_product_name=entry.raw_product_name or None,
            raw_post_text=entry.notes or None,
            product_group=product_group,
            recorded_date=record_date,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return {"success": True, "id": record.id, "message": "تم حفظ السعر بنجاح"}

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


class BulkPriceEntry(BaseModel):
    lines: str
    source: str = "يدوي"
    recorded_date: Optional[date] = None


@router.post("/prices/bulk")
async def create_bulk_prices(body: BulkPriceEntry, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    from app.models import PriceRecord
    from app.services.scrapers.facebook_scraper import _parse_arabic_price_lines

    try:
        record_date = body.recorded_date or date.today()
        parsed_lines, rejected_lines = _parse_arabic_price_lines(body.lines)

        saved = 0
        for pl in parsed_lines:
            unit = pl.get("unit", "per_unit")
            if pl["product_type"] == "fertilized_eggs" and unit == "per_tray":
                unit = "per_unit"
            record = PriceRecord(
                product_type=pl["product_type"],
                category=pl["category"],
                price=pl["price"],
                currency="EGP",
                unit=unit,
                market="manual",
                source=body.source,
                raw_product_name=pl["raw_line"],
                product_group=pl["product_group"],
                recorded_date=record_date,
            )
            db.add(record)
            saved += 1

        await db.commit()

        return {
            "success": True,
            "saved_count": saved,
            "failed_count": len(rejected_lines),
            "failed_lines": rejected_lines[:20],
            "message": f"تم حفظ {saved} سعر بنجاح",
        }

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
