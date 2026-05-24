from sqlalchemy import Column, Integer, String, Float, Date, DateTime, func
from app.db.session import Base


class PriceRecord(Base):
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="EGP")
    unit = Column(String(30), nullable=False)
    market = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    recorded_date = Column(Date, nullable=False, index=True)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class HolidayCalendar(Base):
    __tablename__ = "holiday_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False, unique=True)
    holiday_type = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(50), nullable=False, index=True)
    predicted_price = Column(Float, nullable=False)
    predicted_date = Column(Date, nullable=False)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
