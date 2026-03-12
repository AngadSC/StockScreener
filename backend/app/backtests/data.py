from __future__ import annotations

from datetime import date, timedelta
from typing import List, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.providers.factory import ProviderFactory
from app.services.stock_service import get_price_history
from app.utils.market_calendar import detect_missing_days, get_trading_days_between


def _normalize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date" in out.columns:
        out = out.set_index("date")
    out.index = pd.to_datetime(out.index).date
    expected = ["Open", "High", "Low", "Close", "Volume"]
    available = [col for col in expected if col in out.columns]
    return out[available].sort_index()


def load_backtest_market_data(
    db: Session,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    max_missing_ratio: float = 0.05,
) -> Tuple[pd.DataFrame, str, List[str]]:
    """
    Load OHLCV data from PostgreSQL first and fall back to yfinance when the DB
    range is missing trading days.
    """
    warnings: List[str] = []

    df_db = get_price_history(db, ticker, start_date, end_date, use_cache=False)
    if not df_db.empty:
        df_db = _normalize_market_frame(df_db)
        missing_days = detect_missing_days(df_db.index.tolist(), start_date, end_date)
        if not missing_days:
            return df_db, "database", warnings
        expected_days = get_trading_days_between(start_date, end_date)
        missing_ratio = (len(missing_days) / len(expected_days)) if expected_days else 0.0
        if missing_ratio <= max_missing_ratio:
            warnings.append(
                f"Database range was missing {len(missing_days)} trading day(s) "
                f"({missing_ratio * 100:.2f}% of trading days); using the partial DB range."
            )
            return df_db, "database", warnings

        warnings.append(
            f"Database range was missing {len(missing_days)} trading day(s) "
            f"({missing_ratio * 100:.2f}% of trading days); used yfinance fallback."
        )

    provider = ProviderFactory.get_historical_provider()
    # yfinance treats end as exclusive; pad by a day and filter back down.
    df_yf = provider.get_historical_prices(ticker, start_date, end_date + timedelta(days=1))
    if df_yf is not None and not df_yf.empty:
        df_yf = _normalize_market_frame(df_yf)
        df_yf = df_yf[(df_yf.index >= start_date) & (df_yf.index <= end_date)]
        if not df_yf.empty:
            return df_yf, "yfinance", warnings

    if not df_db.empty:
        warnings.append("yfinance fallback failed; using the partial database range that was available.")
        return df_db, "database", warnings

    raise ValueError(f"No historical data available for {ticker} in the specified period.")
