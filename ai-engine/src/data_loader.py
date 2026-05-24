"""
Data loader — fetches price records from PostgreSQL into a pandas DataFrame.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import DATABASE_URL


def load_price_data(product_type: str, years: int = 3) -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    query = text("""
        SELECT recorded_date AS ds, price AS y, region, category
        FROM price_records
        WHERE product_type = :product_type
          AND recorded_date >= CURRENT_DATE - INTERVAL ':years years'
        ORDER BY recorded_date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"product_type": product_type, "years": years})
    return df
