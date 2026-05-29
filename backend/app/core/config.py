from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache
import os


_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(_BACKEND_DIR, ".env"),
        extra="ignore",
    )

    app_name: str = "Poultry Market Intel API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/poultry_market"
    database_sync_url: str = "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/poultry_market"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    admin_token: str = ""
    env: str = "development"
    log_level: str = "info"
    scheduler_enabled: bool = True

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        if self.env == "production" and not self.admin_token:
            raise ValueError(
                "ADMIN_TOKEN is required when ENV=production. "
                "Set a strong token in .env or environment variables."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
