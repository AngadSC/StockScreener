from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Mapping

import pandas as pd
import yfinance as yf


PROVIDER = "yfinance"
DAILY_INTERVAL = "1d"
OHLC_COLUMNS = ("Open", "High", "Low", "Close")
VOLUME_COLUMN = "Volume"


def _base_result(
    *,
    ticker: str | None = None,
    period: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "provider": PROVIDER,
        "interval": DAILY_INTERVAL,
        "fetched_count": 0,
        "valid_count": 0,
        "dropped_count": 0,
        "error": error,
        "candles": [],
    }
    if ticker is not None:
        result["ticker"] = ticker
    if period is not None:
        result["period"] = period
    return result


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(numeric):
        return None
    return numeric


def _volume(value: Any) -> int | None:
    numeric = _number(value)
    if numeric is None or numeric <= 0:
        return None
    return int(numeric)


def _date(value: Any) -> date | None:
    if _is_missing(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().date()
        except (AttributeError, ValueError, TypeError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return None


def _row_date(index_value: Any, row: Any) -> date | None:
    index_date = _date(index_value)
    if index_date is not None:
        return index_date
    return _date(_row_value(row, "date")) or _date(_row_value(row, "Date"))


def normalize_yfinance_history(history: Any) -> dict[str, Any]:
    result = _base_result()
    if history is None:
        return result

    if not hasattr(history, "iterrows"):
        result["error"] = "history must be a pandas DataFrame or dataframe-like object"
        return result

    try:
        fetched_count = len(history)
    except TypeError:
        fetched_count = 0

    candles: list[dict[str, Any]] = []
    dropped_count = 0
    for index_value, row in history.iterrows():
        candle_date = _row_date(index_value, row)
        open_price = _number(_row_value(row, "Open"))
        high = _number(_row_value(row, "High"))
        low = _number(_row_value(row, "Low"))
        close = _number(_row_value(row, "Close"))
        volume = _volume(_row_value(row, "Volume"))

        if (
            candle_date is None
            or open_price is None
            or high is None
            or low is None
            or close is None
            or volume is None
        ):
            dropped_count += 1
            continue

        candles.append(
            {
                "date": candle_date,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    candles.sort(key=lambda candle: candle["date"])
    result.update(
        {
            "fetched_count": fetched_count,
            "valid_count": len(candles),
            "dropped_count": dropped_count,
            "candles": candles,
        }
    )
    return result


def fetch_yfinance_daily_history(ticker: str, period: str = "1y") -> dict[str, Any]:
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        return _base_result(ticker=normalized_ticker, period=period, error="ticker is required")

    try:
        history = yf.Ticker(normalized_ticker).history(
            period=period,
            interval=DAILY_INTERVAL,
            auto_adjust=False,
            actions=False,
        )
    except Exception as exc:
        return _base_result(ticker=normalized_ticker, period=period, error=str(exc))

    result = normalize_yfinance_history(history)
    result.update({"ticker": normalized_ticker, "period": period})
    return result
