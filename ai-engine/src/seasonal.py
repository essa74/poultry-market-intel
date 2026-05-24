"""
Seasonal effect analyzer — detects price patterns around holidays and seasons.
"""
import pandas as pd
from src.data_loader import load_price_data


def analyze_seasonal_effects(product_type: str, years: int = 3) -> dict:
    df = load_price_data(product_type, years=years)
    if df.empty:
        return {}

    df["month"] = pd.to_datetime(df["ds"]).dt.month
    monthly_avg = df.groupby("month")["y"].mean().to_dict()

    return {
        "product_type": product_type,
        "monthly_averages": monthly_avg,
        "peak_month": max(monthly_avg, key=monthly_avg.get),
        "low_month": min(monthly_avg, key=monthly_avg.get),
    }
