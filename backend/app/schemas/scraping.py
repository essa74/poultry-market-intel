from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import Optional, Any
import re


class ScrapingSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    url: str
    is_active: bool
    health_score: float
    consecutive_failures: int
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    config: Optional[dict] = None
    created_at: datetime
    latest_log: Optional["ScrapingLogResponse"] = None

    class Config:
        from_attributes = True


class ScrapingLogResponse(BaseModel):
    id: int
    source_id: int
    job_id: Optional[str] = None
    status: str
    records_collected: int
    records_skipped: int
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    fetched_text: Optional[str] = None
    html_snapshot_path: Optional[str] = None
    raw_content_length: Optional[int] = None
    selector_matches: Optional[int] = None
    admin_warning: Optional[str] = None
    valid_saved: int = 0
    duplicates_skipped: int = 0
    invalid_skipped: int = 0

    class Config:
        from_attributes = True


class RawPriceResponse(BaseModel):
    id: int
    source_id: int
    raw_text: Optional[str] = None
    product_type: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    region: Optional[str] = None
    recorded_date: Optional[date] = None
    extraction_method: str
    confidence: float
    is_duplicate: bool
    is_failed_sample: bool = False
    product_group: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScraperStatusResponse(BaseModel):
    total_sources: int
    active_sources: int
    healthy_sources: int
    failed_sources: int
    total_logs_today: int
    total_collected_today: int
    scheduler_running: bool
    auto_discover_active: bool = False
    auto_discover_interval_hours: int = 3
    latest_success_at: Optional[datetime] = None
    latest_failure_at: Optional[datetime] = None
    total_valid_saved: int = 0
    total_duplicates_skipped: int = 0
    total_invalid_skipped: int = 0


class ScrapingRunResponse(BaseModel):
    message: str
    status: str


class DebugItem(BaseModel):
    raw_text: str
    product_type: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    region: Optional[str] = None
    confidence: float
    extraction_method: str
    is_duplicate: bool
    is_failed_sample: bool = False


class UpdatePostUrlsRequest(BaseModel):
    post_urls: list[str] = []
    auto_discover: Optional[bool] = None
    max_posts_scan: Optional[int] = None
    max_price_posts: Optional[int] = None


class CreateSourceRequest(BaseModel):
    name: str
    source_type: str = "website"
    url: str
    config: dict = {}
    is_active: bool = True

    @field_validator("source_type")
    @classmethod
    def check_source_type(cls, v: str) -> str:
        allowed = {"website", "facebook", "telegram"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}")
        return v

    @field_validator("url")
    @classmethod
    def normalize_url(cls, url: str) -> str:
        url = url.strip()
        if not url:
            raise ValueError("URL is required")
        m = re.match(r"(?:https?://)?(?:www\.)?t\.me/s/(.+)", url)
        if m:
            return f"https://t.me/s/{m.group(1)}"
        m = re.match(r"(?:https?://)?(?:www\.)?t\.me/(.+?)(?:/.*)?$", url)
        if m:
            return f"https://t.me/s/{m.group(1)}"
        if not re.match(r"https?://", url):
            url = "https://" + url
        if not re.match(r"https?://\S+\.\S+", url):
            raise ValueError("URL must be a valid web address")
        return url


class ScrapingDebugResponse(BaseModel):
    source: ScrapingSourceResponse
    latest_log: Optional[ScrapingLogResponse] = None
    raw_text_preview: Optional[str] = None
    total_items_fetched: int
    items: list[DebugItem] = []
    used_structured_only: bool = False
    structured_items_count: int = 0
    parsed_price_lines_count: int = 0


class PerPostDebug(BaseModel):
    url: str
    text_length: int = 0
    images_found: list[str] = []
    ocr_text_preview: list[str] = []
    extracted_numbers: list[float] = []
    status: str = "pending"


class StructuredMatch(BaseModel):
    url: str = ""
    text: str = ""
    product_group: str = ""
    product_type: str = ""
    category: str = ""
    price: Optional[float] = None
    unit: Optional[str] = None


class NormalizedProduct(BaseModel):
    product_type: str = ""
    category: str = ""
    price: Optional[float] = None
    unit: Optional[str] = None
    product_group: Optional[str] = None


class OcrPreviewItem(BaseModel):
    image_url: str
    raw_ocr: str = ""
    cleaned_ocr: str = ""
    extracted_product: Optional[str] = None
    extracted_price: Optional[float] = None
    confidence: float = 0.0
    score: int = 0
    accepted: bool = False


class ParsedPriceLine(BaseModel):
    raw_line: str = ""
    normalized_line: str = ""
    product_group: str = ""
    product_type: str = ""
    category: str = ""
    price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    unit: Optional[str] = None
    raw_price_range: Optional[str] = None
    confidence: float = 0.0


class ExtractedRecordPreview(BaseModel):
    product_type: str = ""
    category: str = ""
    price: Optional[float] = None
    unit: Optional[str] = None
    product_group: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0


class FacebookDebugResponse(BaseModel):
    source: ScrapingSourceResponse
    strategy_used: Optional[str] = None
    page_id: Optional[str] = None
    attempted_urls: list[str] = []
    fetched_lengths: dict[str, int] = {}
    posts_found: int = 0
    accepted_posts: int = 0
    rejected_posts: int = 0
    rejected_reasons: list[str] = []
    sample_post_texts: list[str] = []
    facebook_blocked: bool = False
    facebook_block_reason: Optional[str] = None
    image_only_detected: bool = False
    fetch_errors: list[str] = []
    playwright_urls: list[str] = []
    playwright_error: Optional[str] = None
    ocr_text_preview: list[str] = []
    normalized_ocr_text: list[str] = []
    image_urls_found: list[str] = []
    extracted_numbers: list[float] = []
    see_more_clicked: int = 0
    ocr_items_created: int = 0
    ocr_error: Optional[str] = None
    ocr_available: bool = False
    all_images_count: int = 0
    rejected_image_urls_sample: list[str] = []
    accepted_post_images: list[str] = []
    image_filter_reasons: list[str] = []
    per_post_debug: list[PerPostDebug] = []
    posts_used: int = 0
    ocr_confidence_avg: float = 0.0
    accepted_ocr_lines: int = 0
    rejected_ocr_lines: int = 0
    structured_matches: list[StructuredMatch] = []
    normalized_products: list[NormalizedProduct] = []
    admin_warning: Optional[str] = None
    cached: bool = False
    page_load_seconds: Optional[float] = None
    image_collect_seconds: Optional[float] = None
    ocr_seconds: Optional[float] = None
    total_seconds: Optional[float] = None
    partial: bool = False
    timeout: bool = False
    message: Optional[str] = None
    raw_text_preview: Optional[str] = None
    direct_post_text: Optional[str] = None
    parsed_price_lines: list[ParsedPriceLine] = []
    rejected_lines: list[str] = []
    extracted_records_preview: list[ExtractedRecordPreview] = []
    used_structured_only: bool = False
    structured_items_count: int = 0
    parsed_price_lines_count: int = 0
