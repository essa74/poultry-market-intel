from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.schemas import HolidayEventResponse
from app.services.holiday_calendar_service import (
    get_holidays,
    get_upcoming_events,
    get_active_events,
    get_event_impact,
    get_all_event_types,
    seed_holidays,
)

router = APIRouter()


@router.get("/", response_model=list[HolidayEventResponse])
async def list_holidays(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await get_holidays(db, from_date=from_date, to_date=to_date, event_type=event_type, limit=limit)


@router.get("/upcoming", response_model=list[HolidayEventResponse])
async def upcoming_holidays(
    days: int = Query(60, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await get_upcoming_events(db, days=days)


@router.get("/active", response_model=list[HolidayEventResponse])
async def active_holidays(
    db: AsyncSession = Depends(get_db),
):
    return await get_active_events(db)


@router.get("/impact")
async def holiday_impact(
    product_type: str = Query(...),
    target_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    impact = await get_event_impact(db, product_type, target_date)
    return {"product_type": product_type, "target_date": target_date or date.today(), "impact_percentage": impact}


@router.get("/types", response_model=list[str])
async def list_event_types(
    db: AsyncSession = Depends(get_db),
):
    return await get_all_event_types(db)


@router.post("/seed")
async def seed(
    years: Optional[str] = Query(None, description="Comma-separated years, e.g. 2026,2027"),
    db: AsyncSession = Depends(get_db),
):
    if years:
        year_list = [int(y.strip()) for y in years.split(",")]
    else:
        year_list = None
    count = await seed_holidays(db, years=year_list)
    return {"message": f"Seeded {count} holiday events", "count": count}
