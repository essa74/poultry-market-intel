"""
Forecasting engine using Meta's Prophet with holiday/seasonality effects.
"""
import pandas as pd
from prophet import Prophet
from typing import Optional
from src.data_loader import load_price_data


def build_model() -> Prophet:
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.05,
    )
    # Ramadan, Eid, Sham El-Nessim, Christian holidays
    model.add_country_holidays(country_name="EG")
    return model


def train_and_forecast(
    product_type: str,
    periods: int = 90,
    years: int = 3,
    monthly: bool = False,
) -> Optional[pd.DataFrame]:
    df = load_price_data(product_type, years=years)
    if df.empty:
        return None

    # Aggregate to daily mean if multiple records per day
    df = df.groupby("ds", as_index=False)["y"].mean()

    model = build_model()
    model.fit(df)

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
