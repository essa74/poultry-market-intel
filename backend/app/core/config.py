from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Poultry Market Intel API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://poultry:poultry@localhost:5432/poultry_market"
    database_sync_url: str = "postgresql+psycopg2://poultry:poultry@localhost:5432/poultry_market"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
