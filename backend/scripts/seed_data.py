"""
Standalone seed script — restores default scraping sources, holidays,
and optionally generates sample price records if the DB is empty.

Usage:
    python -m scripts.seed_data
    python -m scripts.seed_data --no-sample          # skip sample prices
    python -m scripts.seed_data --years 2025 2026    # specific holiday years
"""
import asyncio
import logging
import argparse
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("seed")


async def seed(db):
    from app.services.scrapers import seed_default_sources
    from app.services.holiday_calendar_service import seed_holidays
    from app.models import PriceRecord
    from sqlalchemy import select, func

    logger.info("Seeding default scraping sources...")
    await seed_default_sources(db)
    logger.info("Default sources done.")

    logger.info("Seeding holiday calendar...")
    count = await seed_holidays(db)
    logger.info(f"Holiday calendar done — {count} events.")

    return db


async def seed_sample_prices(db):
    from app.services.scrapers.registry import seed_sample_prices as _seed
    return await _seed(db)


async def main():
    parser = argparse.ArgumentParser(description="Seed database with default data")
    parser.add_argument("--no-sample", action="store_true", help="Skip sample price data")
    parser.add_argument("--years", nargs="+", type=int, default=None,
                        help="Holiday years to seed (default: current + 2)")
    args = parser.parse_args()

    from app.db.session import async_session

    async with async_session() as db:
        await seed(db)
        if not args.no_sample:
            await seed_sample_prices(db)

    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
