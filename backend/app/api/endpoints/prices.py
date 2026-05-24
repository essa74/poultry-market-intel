from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.models import PriceRecord
from app.schemas import PriceRecordCreate, PriceRecordResponse

router = APIRouter()


@router.get("/", response_model=list[PriceRecordResponse])
async def list_prices(
    product_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PriceRecord)
    if product_type:
        stmt = stmt.where(PriceRecord.product_type == product_type)
    if start_date:
        stmt = stmt.where(PriceRecord.recorded_date >= start_date)
    if end_date:
        stmt = stmt.where(PriceRecord.recorded_date <= end_date)
    stmt = stmt.order_by(PriceRecord.recorded_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=PriceRecordResponse, status_code=201)
async def create_price(price: PriceRecordCreate, db: AsyncSession = Depends(get_db)):
    record = PriceRecord(**price.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
