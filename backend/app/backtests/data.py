from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.database.models import DailyOHLCV, Ticker
from app.providers.factory import ProviderFactory
from app.services.stock_service import get_price_history
from app.utils.market_calendar import detect_missing_days, get_trading_days_between


def _normalize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date" in out.columns:
        out = out.set_index("date")
    out.index = pd.to_datetime(out.index).date
    expected = ["Open", "High", "Low", "Close", "Volume"]
    for col in expected:
        if col not in out.columns:
            out[col] = 0 if col == "Volume" else pd.NA
    out = out[expected].sort_index()
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    out["Volume"] = out["Volume"].fillna(0)
    return out


def _coverage_ratio(df: pd.DataFrame, start_date: date, end_date: date) -> tuple[int, int, float]:
    expected_days = get_trading_days_between(start_date, end_date)
    expected_count = len(expected_days)
    if expected_count <= 0:
        return 0, len(df), 1.0
    actual_days = {pd.to_datetime(item).date() for item in df.index.tolist()}
    covered_count = len(set(expected_days) & actual_days)
    return expected_count, covered_count, covered_count / expected_count


def _has_minimum_history(
    df: pd.DataFrame,
    start_date: date,
    end_date: date,
    *,
    min_required_bars: int,
    min_coverage_ratio: float,
) -> bool:
    if len(df) < min_required_bars:
        return False
    _, _, coverage = _coverage_ratio(df, start_date, end_date)
    return coverage >= min_coverage_ratio


def _skip_reason(
    df: pd.DataFrame,
    start_date: date,
    end_date: date,
    *,
    min_required_bars: int,
    min_coverage_ratio: float,
) -> str:
    expected_count, covered_count, coverage = _coverage_ratio(df, start_date, end_date)
    if len(df) < min_required_bars:
        return f"{len(df)} bars; need at least {min_required_bars}"
    if expected_count and coverage < min_coverage_ratio:
        return f"{covered_count}/{expected_count} requested trading days covered ({coverage * 100:.1f}%)"
    return "insufficient usable OHLCV rows"


def load_backtest_market_data_batch_db_only(
    db: Session,
    tickers: List[str],
    start_date: date,
    end_date: date,
    *,
    min_required_bars: int,
    min_coverage_ratio: float = 0.90,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str], List[str]]:
    """
    Load OHLCV data for a server-side universe with a single PostgreSQL query.

    This intentionally never falls back to yfinance. It is used for large
    automated universes where per-symbol provider calls are too expensive.
    """
    symbols = []
    seen: set[str] = set()
    for raw_symbol in tickers:
        symbol = str(raw_symbol).strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)

    if not symbols:
        return {}, {}, ["No symbols were provided for the DB-only universe load."]

    rows = (
        db.query(
            Ticker.symbol,
            DailyOHLCV.date,
            DailyOHLCV.open,
            DailyOHLCV.high,
            DailyOHLCV.low,
            DailyOHLCV.close,
            DailyOHLCV.volume,
        )
        .join(DailyOHLCV, DailyOHLCV.ticker_id == Ticker.id)
        .filter(
            Ticker.symbol.in_(symbols),
            DailyOHLCV.date >= start_date,
            DailyOHLCV.date <= end_date,
        )
        .order_by(Ticker.symbol.asc(), DailyOHLCV.date.asc())
        .all()
    )

    by_symbol: dict[str, list[dict[str, object]]] = {symbol: [] for symbol in symbols}
    for symbol, row_date, open_, high, low, close, volume in rows:
        normalized_symbol = str(symbol).upper()
        if normalized_symbol not in by_symbol:
            continue
        by_symbol[normalized_symbol].append(
            {
                "date": row_date,
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
            }
        )

    market_data: dict[str, pd.DataFrame] = {}
    data_sources: dict[str, str] = {}
    skipped: dict[str, str] = {}

    for symbol in symbols:
        symbol_rows = by_symbol.get(symbol) or []
        if not symbol_rows:
            skipped[symbol] = "no DB rows in requested range"
            continue
        df = _normalize_market_frame(pd.DataFrame(symbol_rows))
        if _has_minimum_history(
            df,
            start_date,
            end_date,
            min_required_bars=min_required_bars,
            min_coverage_ratio=min_coverage_ratio,
        ):
            market_data[symbol] = df
            data_sources[symbol] = "database"
            continue
        skipped[symbol] = _skip_reason(
            df,
            start_date,
            end_date,
            min_required_bars=min_required_bars,
            min_coverage_ratio=min_coverage_ratio,
        )

    warnings: list[str] = []
    if skipped:
        warnings.append(f"Skipped {len(skipped)} symbols with insufficient DB history.")
        sample = ", ".join(f"{symbol} ({reason})" for symbol, reason in list(skipped.items())[:8])
        if sample:
            warnings.append(f"Skipped symbol details: {sample}.")

    return market_data, data_sources, warnings


def load_backtest_market_data(
    db: Session,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    max_missing_ratio: float = 0.10,
    min_required_bars: int = 1,
    min_coverage_ratio: float = 0.90,
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
        if not missing_days and len(df_db) >= min_required_bars:
            return df_db, "database", warnings
        expected_days = get_trading_days_between(start_date, end_date)
        missing_ratio = (len(missing_days) / len(expected_days)) if expected_days else 0.0
        if (
            missing_ratio <= max_missing_ratio
            and _has_minimum_history(
                df_db,
                start_date,
                end_date,
                min_required_bars=min_required_bars,
                min_coverage_ratio=min_coverage_ratio,
            )
        ):
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
        if _has_minimum_history(
            df_yf,
            start_date,
            end_date,
            min_required_bars=min_required_bars,
            min_coverage_ratio=min_coverage_ratio,
        ):
            return df_yf, "yfinance", warnings

    if not df_db.empty and _has_minimum_history(
        df_db,
        start_date,
        end_date,
        min_required_bars=min_required_bars,
        min_coverage_ratio=min_coverage_ratio,
    ):
        warnings.append("yfinance fallback failed; using the partial database range that was available.")
        return df_db, "database", warnings

    raise ValueError(f"No historical data available for {ticker} in the specified period.")
