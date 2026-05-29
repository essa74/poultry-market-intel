from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, func,
    Text, Boolean, Enum as SAEnum, ForeignKey, JSON,
)
from app.db.session import Base
import enum


class ScrapingSourceType(str, enum.Enum):
    WEBSITE = "website"
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"


class ScrapingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class ScrapingSource(Base):
    __tablename__ = "scraping_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    source_type = Column(
        SAEnum(ScrapingSourceType, values_callable=_enum_values), nullable=False
    )
    url = Column(String(500), nullable=False)
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    health_score = Column(Float, default=100.0)
    consecutive_failures = Column(Integer, default=0)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScrapingLog(Base):
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("scraping_sources.id"), nullable=False)
    job_id = Column(String(100), nullable=True, index=True)
    status = Column(
        SAEnum(ScrapingJobStatus, values_callable=_enum_values), nullable=False
    )
    records_collected = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    fetched_text = Column(Text, nullable=True)
    html_snapshot_path = Column(String(500), nullable=True)
    raw_content_length = Column(Integer, nullable=True)
    selector_matches = Column(Integer, nullable=True)
    admin_warning = Column(Text, nullable=True)
    valid_saved = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    invalid_skipped = Column(Integer, default=0)


class RawExtractedPrice(Base):
    __tablename__ = "raw_extracted_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("scraping_sources.id"), nullable=False)
    log_id = Column(Integer, ForeignKey("scraping_logs.id"), nullable=True)
    raw_text = Column(Text, nullable=True)
    product_type = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="EGP")
    unit = Column(String(30), nullable=True)
    region = Column(String(100), nullable=True)
    recorded_date = Column(Date, nullable=True)
    extraction_method = Column(String(50), default="regex")
    confidence = Column(Float, default=0.0)
    is_normalized = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    is_failed_sample = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, nullable=True)
    matched_record_id = Column(Integer, ForeignKey("price_records.id"), nullable=True)
    product_group = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
