from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ai.ohlcv_quality import OHLCVQualityConfig, assess_ohlcv_quality
from app.utils.market_calendar import get_trading_days_between


@dataclass(frozen=True)
class CandleObject:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


def _candle(candle_date: date, volume: int | None = 1000) -> dict[str, object]:
    return {
        "date": candle_date.isoformat(),
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.0,
        "volume": volume,
    }


def _quality_config(min_swing_candles: int = 1) -> OHLCVQualityConfig:
    return OHLCVQualityConfig(
        min_swing_candles=min_swing_candles,
        recent_volume_window=20,
        recent_gap_lookback_trading_days=20,
    )


def test_no_candles_returns_structured_gap_metadata() -> None:
    quality = assess_ohlcv_quality([], expected_latest_date=date(2026, 5, 8))

    assert quality == {
        "has_gaps": True,
        "reasons": ["no_candles"],
        "latest_db_date": None,
        "expected_latest_date": "2026-05-08",
        "missing_dates": [],
        "invalid_candle_dates": [],
        "initial_candle_count": 0,
        "warnings": ["No OHLCV candles were provided."],
    }


def test_insufficient_candles_are_reported_for_swing_analysis() -> None:
    candles = [_candle(day) for day in get_trading_days_between(date(2026, 5, 1), date(2026, 5, 8))]

    quality = assess_ohlcv_quality(
        candles,
        expected_latest_date=date(2026, 5, 8),
        config=_quality_config(min_swing_candles=10),
    )

    assert quality["has_gaps"] is True
    assert quality["reasons"] == ["insufficient_candles_for_swing_analysis"]
    assert quality["initial_candle_count"] == 6
    assert quality["latest_db_date"] == "2026-05-08"
    assert quality["missing_dates"] == []


def test_stale_latest_candle_and_missing_recent_trading_days_are_detected() -> None:
    candles = [
        _candle(date(2026, 5, 1)),
        _candle(date(2026, 5, 5)),
    ]

    quality = assess_ohlcv_quality(
        candles,
        expected_latest_date=date(2026, 5, 5),
        config=_quality_config(),
    )

    assert quality["has_gaps"] is True
    assert quality["reasons"] == ["missing_recent_trading_days"]
    assert quality["missing_dates"] == ["2026-05-04"]

    stale_quality = assess_ohlcv_quality(
        [_candle(date(2026, 5, 1))],
        expected_latest_date=date(2026, 5, 5),
        config=_quality_config(),
    )

    assert "latest_candle_stale" in stale_quality["reasons"]
    assert stale_quality["missing_dates"] == ["2026-05-04", "2026-05-05"]


def test_weekends_do_not_create_missing_date_false_positives() -> None:
    quality = assess_ohlcv_quality(
        [
            _candle(date(2026, 5, 7)),
            _candle(date(2026, 5, 8)),
        ],
        as_of_date=date(2026, 5, 10),
        config=_quality_config(),
    )

    assert quality["has_gaps"] is False
    assert quality["reasons"] == []
    assert quality["latest_db_date"] == "2026-05-08"
    assert quality["expected_latest_date"] == "2026-05-08"
    assert quality["missing_dates"] == []


def test_market_holidays_do_not_create_missing_date_false_positives() -> None:
    quality = assess_ohlcv_quality(
        [_candle(date(2026, 7, 2))],
        as_of_date=date(2026, 7, 5),
        config=_quality_config(),
    )

    assert quality["has_gaps"] is False
    assert quality["latest_db_date"] == "2026-07-02"
    assert quality["expected_latest_date"] == "2026-07-02"
    assert quality["missing_dates"] == []


def test_null_ohlcv_fields_and_recent_invalid_volume_dates_are_reported() -> None:
    days = get_trading_days_between(date(2026, 1, 5), date(2026, 1, 30))
    candles = [_candle(day) for day in days]
    candles[3]["open"] = None
    candles[-1]["volume"] = 0

    quality = assess_ohlcv_quality(
        candles,
        expected_latest_date=days[-1],
        config=_quality_config(),
    )

    assert quality["has_gaps"] is True
    assert quality["reasons"] == ["null_ohlcv_fields", "invalid_recent_volume"]
    assert quality["invalid_candle_dates"] == [days[3].isoformat(), days[-1].isoformat()]
    assert quality["missing_dates"] == []


def test_lightweight_object_candles_are_supported() -> None:
    candles = [
        CandleObject(
            date=candle_date,
            open=20.0,
            high=21.0,
            low=19.0,
            close=20.5,
            volume=2000,
        )
        for candle_date in get_trading_days_between(date(2026, 3, 2), date(2026, 3, 6))
    ]

    quality = assess_ohlcv_quality(
        candles,
        expected_latest_date=date(2026, 3, 6),
        config=_quality_config(),
    )

    assert quality["has_gaps"] is False
    assert quality["initial_candle_count"] == 5
    assert quality["latest_db_date"] == "2026-03-06"
