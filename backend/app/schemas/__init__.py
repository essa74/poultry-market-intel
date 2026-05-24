from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class PriceRecordCreate(BaseModel):
    product_type: str = Field(..., example="fertilized_eggs")
    category: str = Field(..., example="white")
    price: float = Field(..., gt=0)
    currency: str = "EGP"
    unit: str = Field(..., example="per_1000")
    market: Optional[str] = None
    region: Optional[str] = None
    recorded_date: date
    source: Optional[str] = None


class PriceRecordResponse(PriceRecordCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceTrendQuery(BaseModel):
    product_type: str
    start_date: date
    end_date: date
    region: Optional[str] = None


class PredictionResponse(BaseModel):
    id: int
    product_type: str
    predicted_price: float
    predicted_date: date
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_version: Optional[str] = None

    class Config:
        from_attributes = True
