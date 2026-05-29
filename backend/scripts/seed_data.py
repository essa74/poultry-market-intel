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
    from app.models import PriceRecord
    from sqlalchemy import select, func

    result = await db.execute(select(func.count(PriceRecord.id)))
    total = result.scalar() or 0
    if total > 0:
        logger.info(f"Price records table already has {total} rows — skipping sample data.")
        return

    logger.info("No price records found — generating sample data for 3 days...")

    FEATURED_CATEGORIES = [
        ("white", "أبيض", 58.0),
        ("sasso", "ساسو", 68.0),
        ("baladi", "بلدي", 75.0),
        ("local", "محلي / فيومي وجميزة", 62.0),
        ("duck", "بط", 85.0),
        ("quail", "سمان", 50.0),
        ("turkey", "رومي", 120.0),
        ("ostrich", "نعام", 500.0),
    ]

    today = date.today()
    count = 0
    for day_offset in range(3):
        d = today - timedelta(days=day_offset)
        for cat_key, cat_label, base_price in FEATURED_CATEGORIES:
            price_variation = (day_offset * 1.5) + (hash(cat_key + str(d)) % 10 - 5) * 0.5
            record = PriceRecord(
                product_type="fertilized_eggs",
                category=cat_key,
                price=round(base_price + price_variation, 1),
                currency="EGP",
                unit="per_tray",
                source="بورصة المهدي جروب",
                recorded_date=d,
                raw_product_name=f"بيض مخصب {cat_label}",
                product_group="fertilized_eggs",
            )
            db.add(record)
            count += 1

    # Add a few chick records
    chick_data = [
        ("white", "أبيض", 18.0),
        ("sasso", "ساسو", 15.5),
        ("baladi", "بلدي", 12.0),
    ]
    for day_offset in range(3):
        d = today - timedelta(days=day_offset)
        for cat_key, cat_label, base_price in chick_data:
            variation = (day_offset * 0.3) + (hash(f"chick_{cat_key}{d}") % 10 - 5) * 0.2
            record = PriceRecord(
                product_type="day_old_chicks",
                category=cat_key,
                price=round(base_price + variation, 1),
                currency="EGP",
                unit="per_unit",
                source="بورصة المهدي جروب",
                recorded_date=d,
                raw_product_name=f"كتاكيت {cat_label}",
                product_group="chicks",
            )
            db.add(record)
            count += 1

    await db.commit()
    logger.info(f"Generated {count} sample price records.")


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
