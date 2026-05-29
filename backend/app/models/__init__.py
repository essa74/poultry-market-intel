from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSON
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
    raw_product_name = Column(String(500), nullable=True)
    raw_post_text = Column(Text, nullable=True)
    product_group = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class HolidayCalendar(Base):
    __tablename__ = "holiday_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_ar = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    impact_description = Column(String(200), nullable=True)
    impact_percentage = Column(Float, nullable=True)
    affected_products = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


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


from app.models.scraping import ScrapingSource, ScrapingLog, RawExtractedPrice  # noqa: E402, F401


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(1000), nullable=False, unique=True)
    source_name = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=True, index=True)
    image_url = Column(String(1000), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    keywords = Column(String(500), nullable=True)
    relevance_score = Column(Integer, nullable=True, index=True)
    sentiment = Column(String(20), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
