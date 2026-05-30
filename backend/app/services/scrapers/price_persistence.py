import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import PriceRecord
from app.models.scraping import ScrapingLog, RawExtractedPrice, ScrapingSource

logger = logging.getLogger(__name__)


def normalize_product_type(raw: str) -> str:
    raw_lower = raw.replace(" ", "").lower()
    mapping = {
        "فراخ": "day_old_chicks",
        "كتاكيت": "day_old_chicks",
        "كتكوت": "day_old_chicks",
        "دجاج": "day_old_chicks",
        "عمر يوم": "day_old_chicks",
        "بيضمخصب": "fertilized_eggs",
        "بيضتفريخ": "fertilized_eggs",
        "بيضأمهات": "fertilized_eggs",
        "بيضتسمين": "fertilized_eggs",
        "بيضساسومخصب": "fertilized_eggs",
        "hatchingeggs": "fertilized_eggs",
        "fertileeggs": "fertilized_eggs",
    }
    for key, val in mapping.items():
        if key in raw_lower:
            return val
    return raw


def normalize_category(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw_lower = raw.replace(" ", "").lower()
    mapping = {
        "ابيض": "white",
        "أبيض": "white",
        "بلدي": "baladi",
        "بلدى": "baladi",
        "بني": "brown",
        "أحمر": "brown",
        "احمر": "brown",
        "ساسو": "sasso",
        "رومى": "turkey",
        "رومي": "turkey",
        "محلي": "baladi",
        "هايبرد": "white",
    }
    return mapping.get(raw_lower, raw)


async def save_extracted_price(
    db: AsyncSession,
    source: ScrapingSource,
    log: ScrapingLog,
    raw_item: RawExtractedPrice,
    raw_post_text: Optional[str] = None,
) -> tuple[str, Optional[PriceRecord]]:
    if raw_item.confidence is None or raw_item.confidence <= 0:
        return "invalid", None
    if raw_item.price is None or raw_item.price <= 0:
        return "invalid", None
    if raw_item.is_failed_sample:
        return "invalid", None
    if not raw_item.product_type:
        return "invalid", None

    product_type = normalize_product_type(raw_item.product_type)
    category = normalize_category(raw_item.category) or "unknown"

    recorded_date = raw_item.recorded_date or datetime.utcnow().date()
    raw_product_name = str(getattr(raw_item, "raw_text", "") or "")[:500] or None

    # Dedup 1: same source + recorded_date + raw_product_name + price (exact match)
    dup_filters = [
        PriceRecord.product_type == product_type,
        PriceRecord.price == raw_item.price,
        PriceRecord.source == source.name,
        PriceRecord.recorded_date == recorded_date,
    ]
    if raw_product_name:
        dup_filters.append(PriceRecord.raw_product_name == raw_product_name)

    dup_stmt = select(PriceRecord).where(and_(*dup_filters))
    existing = await db.execute(dup_stmt)
    if existing.first():
        logger.debug(
            f"Duplicate skipped: {product_type} @ {raw_item.price} from {source.name} "
            f"on {recorded_date} (raw={raw_product_name})"
        )
        raw_item.is_duplicate = True
        return "duplicate", None

    # Dedup 2: same source + product_type + category + price within 6h (legacy check)
    cutoff = datetime.utcnow() - timedelta(hours=6)
    stmt = select(PriceRecord).where(
        and_(
            PriceRecord.product_type == product_type,
            PriceRecord.category == category,
            PriceRecord.price == raw_item.price,
            PriceRecord.source == source.name,
            PriceRecord.created_at >= cutoff,
        )
    )
    existing = await db.execute(stmt)
    if existing.first():
        logger.debug(
            f"Duplicate skipped: {product_type}/{category} @ {raw_item.price} from {source.name} within 6h"
        )
        raw_item.is_duplicate = True
        return "duplicate", None

    unit = raw_item.unit
    raw_text = raw_item.raw_text or ""
    if not unit:
        pg = getattr(raw_item, "product_group", None) or ""
        if "كراتين" in raw_text or "كرتونة" in raw_text:
            unit = "per_carton"
        elif pg == "fertilized_eggs":
            unit = "per_unit"
        elif pg in ("chicks", "ducks"):
            unit = "per_unit"
        else:
            unit = "per_unit"
    elif product_type == "fertilized_eggs" and unit == "per_tray":
        unit = "per_unit"

    record = PriceRecord(
        product_type=product_type,
        category=category,
        price=raw_item.price,
        currency=raw_item.currency or "EGP",
        unit=unit,
        region=raw_item.region,
        recorded_date=raw_item.recorded_date or datetime.utcnow().date(),
        source=source.name,
        raw_product_name=str(getattr(raw_item, "raw_text", "") or "")[:500],
        raw_post_text=raw_post_text,
        product_group=getattr(raw_item, "product_group", None) or None,
    )
    db.add(record)
    await db.flush()

    raw_item.matched_record_id = record.id
    raw_item.is_normalized = True

    logger.info(
        f"Price saved: {product_type}/{category} @ {raw_item.price} EGP "
        f"from {source.name}"
    )
    return "saved", record
