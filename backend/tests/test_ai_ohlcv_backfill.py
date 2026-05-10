from __future__ import annotations

from datetime import date

import pandas as pd

from app.ai.ohlcv_backfill import normalize_yfinance_history


def test_normalize_yfinance_history_returns_db_ready_candles_and_metadata() -> None:
    history = pd.DataFrame(
        {
            "Open": [100.0, 101.5],
            "High": [105.0, 106.5],
            "Low": [99.0, 100.5],
            "Close": [104.0, 105.5],
            "Volume": [1_000_000, 1_250_000],
        },
        index=pd.to_datetime(["2026-05-07 09:30:00-04:00", "2026-05-08 09:30:00-04:00"]),
    )

    result = normalize_yfinance_history(history)

    assert result["provider"] == "yfinance"
    assert result["interval"] == "1d"
    assert result["fetched_count"] == 2
    assert result["valid_count"] == 2
    assert result["dropped_count"] == 0
    assert result["error"] is None
    assert result["candles"] == [
        {
            "date": date(2026, 5, 7),
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 1_000_000,
        },
        {
            "date": date(2026, 5, 8),
            "open": 101.5,
            "high": 106.5,
            "low": 100.5,
            "close": 105.5,
            "volume": 1_250_000,
        },
    ]


def test_normalize_yfinance_history_drops_rows_with_missing_ohlc_or_bad_volume() -> None:
    history = pd.DataFrame(
        {
            "Open": [100.0, None, 102.0, 103.0, 104.0],
            "High": [105.0, 106.0, 107.0, 108.0, 109.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "Close": [104.0, 105.0, 106.0, 107.0, 108.0],
            "Volume": [1_000_000, 1_100_000, None, 0, -10],
        },
        index=pd.to_datetime(["2026-05-04", "2026-05-05", "2026-05-06", "2026-05-07", "2026-05-08"]),
    )

    result = normalize_yfinance_history(history)

    assert result["fetched_count"] == 5
    assert result["valid_count"] == 1
    assert result["dropped_count"] == 4
    assert result["candles"] == [
        {
            "date": date(2026, 5, 4),
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 1_000_000,
        }
    ]


def test_normalize_yfinance_history_uses_date_column_when_index_is_not_date_like() -> None:
    history = pd.DataFrame(
        {
            "date": ["2026-05-08", "2026-05-07"],
            "Open": ["101.0", "100.0"],
            "High": ["106.0", "105.0"],
            "Low": ["100.0", "99.0"],
            "Close": ["105.0", "104.0"],
            "Volume": ["1250000", "1000000"],
        }
    )

    result = normalize_yfinance_history(history)

    assert result["valid_count"] == 2
    assert result["dropped_count"] == 0
    assert [candle["date"] for candle in result["candles"]] == [date(2026, 5, 7), date(2026, 5, 8)]
    assert result["candles"][0]["volume"] == 1_000_000


def test_normalize_yfinance_history_handles_empty_or_invalid_history_without_network() -> None:
    empty_result = normalize_yfinance_history(
        pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    )

    assert empty_result["fetched_count"] == 0
    assert empty_result["valid_count"] == 0
    assert empty_result["dropped_count"] == 0
    assert empty_result["candles"] == []
    assert empty_result["error"] is None

    invalid_result = normalize_yfinance_history([{"Open": 1}])

    assert invalid_result["provider"] == "yfinance"
    assert invalid_result["error"] == "history must be a pandas DataFrame or dataframe-like object"
    assert invalid_result["candles"] == []
