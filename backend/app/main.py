import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.api import router
from app.db.session import async_session
from app.services.scrapers import start_scheduler, stop_scheduler, seed_default_sources
from app.services.holiday_calendar_service import seed_holidays
from app.services.news_scraper import refresh_all_news

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing scheduler...")
    try:
        start_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler startup skipped: {e}")

    try:
        async with async_session() as db:
            await seed_default_sources(db)
            await seed_holidays(db)
    except Exception as e:
        logger.warning(f"Startup seeding skipped: {e}")

    yield
    logger.info("Shutting down — stopping scheduler...")
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="Poultry Market Intelligence Platform API — track fertilized egg prices, day-old chick prices, analyze trends, and predict future prices using AI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}
