from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete
from datetime import date, datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from app.db.session import get_db
from app.models import PriceRecord
from app.api.deps import require_admin_token
from app.models.scraping import ScrapingSource
from app.schemas import PriceRecordCreate, PriceRecordResponse

router = APIRouter()


PRODUCT_GROUP_MAP = {
    "fertilized_eggs": "fertilized_eggs",
    "day_old_chicks": "chicks",
    "feed": "feed",
}

UNIT_MAP = {
    "per_tray": "per_tray",
    "per_egg": "per_egg",
    "per_unit": "per_unit",
    "per_ton": "per_ton",
}


class ManualPriceEntry(BaseModel):
    product_type: str = Field(..., pattern=r"^(fertilized_eggs|day_old_chicks|feed)$")
    category: str = Field(..., pattern=r"^(white|sasso|baladi|other|feed_corn|feed_soy)$")
    price: float = Field(..., gt=0)
    unit: str = Field(..., pattern=r"^(per_tray|per_egg|per_unit|per_ton|per_carton)$")
    source_name: str = Field(default="إدخال يدوي")
    raw_note: Optional[str] = None
    recorded_date: Optional[date] = None


@router.post("/manual", response_model=PriceRecordResponse, status_code=201)
async def create_manual_price(entry: ManualPriceEntry, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    record_date = entry.recorded_date or date.today()
    product_group = PRODUCT_GROUP_MAP.get(entry.product_type)
    unit = entry.unit
    if entry.product_type == "fertilized_eggs" and unit == "per_tray":
        unit = "per_unit"
    record = PriceRecord(
        product_type=entry.product_type,
        category=entry.category,
        price=entry.price,
        currency="EGP",
        unit=unit,
        market="manual",
        source=entry.source_name or "إدخال يدوي",
        raw_product_name=entry.raw_note,
        product_group=product_group,
        recorded_date=record_date,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/", response_model=list[PriceRecordResponse])
async def list_prices(
    product_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PriceRecord)
    if product_type:
        stmt = stmt.where(PriceRecord.product_type == product_type)
    if category:
        stmt = stmt.where(PriceRecord.category == category)
    if region:
        stmt = stmt.where(PriceRecord.region == region)
    if start_date:
        stmt = stmt.where(PriceRecord.recorded_date >= start_date)
    if end_date:
        stmt = stmt.where(PriceRecord.recorded_date <= end_date)
    stmt = stmt.order_by(PriceRecord.recorded_date.desc())
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/latest", response_model=list[PriceRecordResponse])
async def latest_prices(
    source_id: Optional[int] = Query(None),
    product_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    # Resolve source_id to source name
    source_name = None
    if source_id:
        src_result = await db.execute(select(ScrapingSource.name).where(ScrapingSource.id == source_id))
        source_name = src_result.scalar_one_or_none()

    # Subquery: latest record per product_type + category + raw_product_name
    subq = (
        select(
            PriceRecord.product_type,
            PriceRecord.category,
            PriceRecord.raw_product_name,
            func.max(PriceRecord.id).label("max_id"),
        )
    )
    if source_name:
        subq = subq.where(PriceRecord.source == source_name)
    if product_type:
        subq = subq.where(PriceRecord.product_type == product_type)
    if category:
        subq = subq.where(PriceRecord.category == category)
    subq = subq.group_by(PriceRecord.product_type, PriceRecord.category, PriceRecord.raw_product_name).subquery()

    stmt = (
        select(PriceRecord)
        .join(subq, PriceRecord.id == subq.c.max_id)
        .order_by(PriceRecord.product_type, PriceRecord.category, PriceRecord.raw_product_name)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/trends", response_model=list[PriceRecordResponse])
async def price_trends(
    product_type: str = Query("fertilized_eggs"),
    days: int = Query(90, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(PriceRecord)
        .where(
            PriceRecord.product_type == product_type,
            PriceRecord.recorded_date >= cutoff,
        )
        .order_by(PriceRecord.recorded_date.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{price_id}", response_model=PriceRecordResponse)
async def get_price(price_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceRecord).where(PriceRecord.id == price_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Price record not found")
    return record


@router.post("/", response_model=PriceRecordResponse, status_code=201)
async def create_price(price: PriceRecordCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    record = PriceRecord(**price.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/{price_id}", response_model=PriceRecordResponse)
async def update_price(price_id: int, price: PriceRecordCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(select(PriceRecord).where(PriceRecord.id == price_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Price record not found")
    for key, val in price.model_dump().items():
        setattr(record, key, val)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{price_id}", status_code=204)
async def delete_price(price_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(select(PriceRecord).where(PriceRecord.id == price_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Price record not found")
    await db.delete(record)
    await db.commit()
    return None
