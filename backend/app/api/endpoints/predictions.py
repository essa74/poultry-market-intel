from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.models import Prediction
from app.schemas import PredictionResponse

router = APIRouter()


@router.get("/", response_model=list[PredictionResponse])
async def list_predictions(
    product_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Prediction)
    if product_type:
        stmt = stmt.where(Prediction.product_type == product_type)
    if from_date:
        stmt = stmt.where(Prediction.predicted_date >= from_date)
    stmt = stmt.order_by(Prediction.predicted_date)
    result = await db.execute(stmt)
    return result.scalars().all()
