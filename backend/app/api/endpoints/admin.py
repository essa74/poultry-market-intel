import logging
import traceback
from fastapi import APIRouter, Depends, UploadFile, File, Form
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


@router.post("/prices/ocr-preview")
async def ocr_preview(
    image: UploadFile = File(...),
    recorded_date: Optional[str] = Form(None),
    _=Depends(require_admin_token),
):
    from app.services.ocr_service import ocr_image, validate_image
    from app.services.scrapers.facebook_scraper import _parse_arabic_price_lines
    from app.services.chick_poster_parser import parse_chick_poster_text, _is_chick_poster
    from app.services.region_detection import detect_regions

    logger.info(f"OCR preview: content_type={image.content_type}, filename={image.filename}")

    if not image.content_type or not image.content_type.startswith("image/"):
        return {"success": False, "error": "يجب رفع ملف صورة (jpg/png/webp)"}

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed:
        return {"success": False, "error": f"صيغة الصورة غير مدعومة: {image.content_type}. الصيغ المدعومة: jpg, png, webp"}

    try:
        image_bytes = await image.read()
    except Exception as e:
        return {"success": False, "error": f"فشل قراءة الصورة: {e}"}

    logger.info(f"OCR preview: image_size={len(image_bytes)} bytes")

    valid, err = validate_image(image_bytes)
    if not valid:
        return {"success": False, "error": err}

    success, extracted_text, error = await ocr_image(image_bytes)
    if not success:
        return {"success": False, "error": error}

    logger.info(f"OCR preview: extracted_text_length={len(extracted_text)}")

    egg_items, egg_rejected = _parse_arabic_price_lines(extracted_text)
    chick_items = []
    region_items = []
    use_region = False

    if not egg_items or _is_chick_poster(extracted_text):
        chick_items, chick_rejected = parse_chick_poster_text(extracted_text)

    if not egg_items and not chick_items:
        region_items = await detect_regions(image_bytes)
        use_region = bool(region_items)

    items = []
    rejected_lines = egg_rejected[:20]

    if chick_items:
        for ci in chick_items:
            unit = ci.get("unit", "per_unit")
            items.append({
                "product_type": ci["product_type"],
                "category": ci["category"],
                "raw_product_name": ci["raw_product_name"],
                "price": ci["price"],
                "unit": unit,
                "confidence": ci.get("confidence", "medium"),
                "confidence_reason": ci.get("confidence_reason", ""),
                "extraction_method": "chick_text",
            })
        if chick_rejected:
            rejected_lines.extend(chick_rejected[:10])
    elif use_region:
        for ri in region_items:
            items.append(ri)
    else:
        for pl in egg_items:
            unit = pl.get("unit", "per_unit")
            if pl["product_type"] == "fertilized_eggs" and unit == "per_tray":
                unit = "per_unit"
            items.append({
                "product_type": pl["product_type"],
                "category": pl["category"],
                "raw_product_name": pl["raw_line"],
                "price": pl["price"],
                "unit": unit,
                "confidence": "high",
                "confidence_reason": "parsed from text",
                "extraction_method": "table_ocr",
            })

    result = {
        "success": True,
        "extracted_text": extracted_text,
        "parsed_items": items,
        "rejected_lines": rejected_lines[:30],
    }

    if not items:
        result["message"] = "لم يتم استخراج أسعار تلقائياً — يمكنك نسخ النص أو إدخال الأسعار يدوياً"

    return result


class OcrSaveItem(BaseModel):
    product_type: str
    category: str
    raw_product_name: str = ""
    price: float
    unit: str = "per_unit"


class OcrSaveBody(BaseModel):
    items: list[OcrSaveItem]
    recorded_date: Optional[date] = None


@router.post("/prices/ocr-save")
async def ocr_save(
    body: OcrSaveBody,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin_token),
):
    from app.models import PriceRecord

    try:
        record_date = body.recorded_date or date.today()
        saved = 0
        for item in body.items:
            unit = item.unit
            if item.product_type == "fertilized_eggs" and unit == "per_tray":
                unit = "per_unit"
            product_group = "fertilized_eggs" if item.product_type == "fertilized_eggs" else "chicks"
            record = PriceRecord(
                product_type=item.product_type,
                category=item.category,
                price=item.price,
                currency="EGP",
                unit=unit,
                market="ocr_market",
                source="ocr_market",
                raw_product_name=item.raw_product_name or None,
                raw_post_text="تم الاستخراج من صورة",
                product_group=product_group,
                recorded_date=record_date,
            )
            db.add(record)
            saved += 1

        await db.commit()

        return {
            "success": True,
            "saved_count": saved,
            "message": f"تم حفظ {saved} سعر بنجاح",
        }

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


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
