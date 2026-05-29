"""
Scraper configuration — Mahdy Group (info-only) + Facebook poultry pages.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class ScraperSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        extra="ignore",
    )

    playwright_headless: bool = True
    playwright_timeout: int = 30_000
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay_minutes: int = 15
    dedup_window_hours: int = 24
    ai_extraction_enabled: bool = True
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    morning_hour: int = 6
    evening_hour: int = 18
    max_sources_per_job: int = 20


@lru_cache
def get_scraper_settings() -> ScraperSettings:
    return ScraperSettings()


DEFAULT_SOURCES = [
    {
        "name": "بورصة المهدي جروب",
        "source_type": "website",
        "url": "https://mahdy-group.com/",
        "is_active": True,
        "config": {
            "selector": "body, .entry-content, .site-content, main, article, .post-content",
            "type": "mahdy",
            "confidence": "medium",
        },
    },
    {
        "name": "إكسبو بيض مصر",
        "source_type": "facebook",
        "url": "https://web.facebook.com/expoeggegypt/",
        "is_active": True,
        "config": {
            "page_id": "expoeggegypt",
            "posts_limit": 10,
            "confidence": "medium",
            "post_urls": [],
        },
    },
    {
        "name": "بيض تفريخ مصر",
        "source_type": "facebook",
        "url": "https://web.facebook.com/HATCHED.EGG.EGYPT/",
        "is_active": True,
        "config": {
            "page_id": "HATCHED.EGG.EGYPT",
            "posts_limit": 10,
            "confidence": "medium",
            "post_urls": [],
        },
    },
]
