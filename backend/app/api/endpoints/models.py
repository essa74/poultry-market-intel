from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.models import PriceRecord, Prediction

router = APIRouter()

MODEL_DEFS = [
    {"model_name": "ARIMA", "required_days": 30},
    {"model_name": "Prophet", "required_days": 45},
    {"model_name": "LSTM", "required_days": 90},
]


class ModelStatusItem(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str
    model_is_trained: bool
    required_days: int
    available_days: int
    can_train: bool
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    forecast_horizon: Optional[int] = None
    last_trained_at: Optional[datetime] = None


class ModelsStatusResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    models: list[ModelStatusItem]
    ensemble_can_train: bool
    data_start_date: Optional[date] = None
    data_end_date: Optional[date] = None


@router.get("/status", response_model=ModelsStatusResponse)
async def models_status(
    product_type: str = Query("fertilized_eggs"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Count distinct dates with data for this product
    count_result = await db.execute(
        select(func.count(func.distinct(PriceRecord.recorded_date)))
        .where(PriceRecord.product_type == product_type)
    )
    available_days = count_result.scalar() or 0

    # 2. Date range
    date_result = await db.execute(
        select(
            func.min(PriceRecord.recorded_date),
            func.max(PriceRecord.recorded_date),
        ).where(PriceRecord.product_type == product_type)
    )
    row = date_result.one()
    data_start = row[0]
    data_end = row[1]

    # 3. Per-model: check for stored predictions with matching model_version
    result = []
    for mdef in MODEL_DEFS:
        can_train = available_days >= mdef["required_days"]

        # Find the latest prediction for this model
        pred_result = await db.execute(
            select(Prediction)
            .where(
                Prediction.product_type == product_type,
                Prediction.model_version == mdef["model_name"],
            )
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        latest_pred = pred_result.scalar_one_or_none()

        model_is_trained = latest_pred is not None
        last_trained = latest_pred.created_at if latest_pred else None
        forecast_horizon = None
        if latest_pred:
            # estimate horizon as days between first and last prediction
            count_pred = await db.execute(
                select(func.count(Prediction.id))
                .where(
                    Prediction.product_type == product_type,
                    Prediction.model_version == mdef["model_name"],
                )
            )
            if count_pred.scalar() and count_pred.scalar() > 1:
                range_result = await db.execute(
                    select(
                        func.min(Prediction.predicted_date),
                        func.max(Prediction.predicted_date),
                    )
                    .where(
                        Prediction.product_type == product_type,
                        Prediction.model_version == mdef["model_name"],
                    )
                )
                min_d, max_d = range_result.one()
                if min_d and max_d:
                    forecast_horizon = (max_d - min_d).days

        mae = rmse = mape = None
        if model_is_trained:
            # Compute metrics: compare past predictions against actual prices
            metrics_result = await db.execute(
                select(Prediction.predicted_date, Prediction.predicted_price)
                .where(
                    Prediction.product_type == product_type,
                    Prediction.model_version == mdef["model_name"],
                    Prediction.predicted_date <= date.today(),
                )
            )
            pred_rows = metrics_result.all()

            if pred_rows:
                errors = []
                for pred_date, pred_price in pred_rows:
                    actual_result = await db.execute(
                        select(func.avg(PriceRecord.price))
                        .where(
                            PriceRecord.product_type == product_type,
                            PriceRecord.recorded_date == pred_date,
                        )
                    )
                    actual_price = actual_result.scalar()
                    if actual_price and actual_price > 0:
                        errors.append({
                            "actual": actual_price,
                            "predicted": pred_price,
                            "abs_error": abs(pred_price - actual_price),
                            "pct_error": abs(pred_price - actual_price) / actual_price * 100,
                        })

                if errors:
                    n = len(errors)
                    mae = sum(e["abs_error"] for e in errors) / n
                    rmse = (sum(e["abs_error"] ** 2 for e in errors) / n) ** 0.5
                    mape = sum(e["pct_error"] for e in errors) / n

        result.append(ModelStatusItem(
            model_name=mdef["model_name"],
            model_is_trained=model_is_trained,
            required_days=mdef["required_days"],
            available_days=available_days,
            can_train=can_train,
            mae=round(mae, 2) if mae is not None else None,
            rmse=round(rmse, 2) if rmse is not None else None,
            mape=round(mape, 2) if mape is not None else None,
            forecast_horizon=forecast_horizon,
            last_trained_at=last_trained,
        ))

    # 4. Ensemble: available if at least 2 individual models are trained
    trained_count = sum(1 for m in result if m.model_is_trained)
    ensemble_can_train = trained_count >= 2

    ensemble_item = ModelStatusItem(
        model_name="Ensemble",
        model_is_trained=ensemble_can_train,
        required_days=max(m.required_days for m in result),
        available_days=available_days,
        can_train=ensemble_can_train,
        mae=None,
        rmse=None,
        mape=None,
        forecast_horizon=max((m.forecast_horizon or 0) for m in result) if any(m.forecast_horizon for m in result) else None,
        last_trained_at=max((m.last_trained_at for m in result if m.last_trained_at), default=None),
    )

    result.append(ensemble_item)

    return ModelsStatusResponse(
        models=result,
        ensemble_can_train=ensemble_can_train,
        data_start_date=data_start,
        data_end_date=data_end,
    )
