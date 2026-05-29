from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class HolidayEventCreate(BaseModel):
    name_ar: str = Field(..., example="شهر رمضان")
    name_en: str = Field(..., example="Ramadan")
    event_type: str = Field(..., example="ramadan")
    start_date: date
    end_date: date
    impact_description: Optional[str] = None
    impact_percentage: Optional[float] = None
    affected_products: Optional[list[str]] = None
    notes: Optional[str] = None


class HolidayEventResponse(HolidayEventCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    raw_product_name: Optional[str] = None
    product_group: Optional[str] = None


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
