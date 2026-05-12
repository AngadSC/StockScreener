from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from app.ai.technical_summary import (
    NormalizedCandle,
    atr_14,
    average_volume,
    build_technical_summary,
    classify_trend,
    high_low,
    latest_candle_summary,
    latest_volume_ratio,
    return_over,
    rsi_14,
    sma,
    sma_20,
    sma_50,
    sma_200,
    sma_distances,
    support_resistance_distances,
)


@dataclass(frozen=True)
class CandleObject:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


def _sample_candles(count: int = 220) -> list[dict[str, float | int | str]]:
    start = date(2025, 1, 1)
    candles = []
    for index in range(count):
        close = 100.0 + index
        candles.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + (index * 10),
            }
        )
    return candles


def test_moving_averages_accept_dict_candles() -> None:
    candles = _sample_candles()

    assert sma_20(candles) == pytest.approx(309.5)
    assert sma_50(candles) == pytest.approx(294.5)
    assert sma_200(candles) == pytest.approx(219.5)
    assert sma(candles, 5) == pytest.approx(317.0)


def test_indicator_helpers_are_deterministic() -> None:
    candles = _sample_candles()

    assert rsi_14(candles) == pytest.approx(100.0)
    assert atr_14(candles) == pytest.approx(4.0)
    assert return_over(candles, 5) == pytest.approx((319.0 - 314.0) / 314.0)
    assert return_over(candles, 60) == pytest.approx((319.0 - 259.0) / 259.0)


def test_volume_and_level_helpers() -> None:
    candles = _sample_candles()

    assert average_volume(candles, 20) == pytest.approx(3095.0)
    assert average_volume(candles, 30) == pytest.approx(3045.0)
    assert average_volume(candles, 50) == pytest.approx(2945.0)
    assert latest_volume_ratio(candles, 20) == pytest.approx(3190.0 / 3095.0)
    assert high_low(candles, 20) == {"high": 321.0, "low": 298.0}
    assert high_low(candles, 60) == {"high": 321.0, "low": 258.0}


def test_distance_helpers_use_latest_close_against_level() -> None:
    candles = _sample_candles()

    support_resistance = support_resistance_distances(candles, 20)
    assert support_resistance["support"] == pytest.approx(298.0)
    assert support_resistance["resistance"] == pytest.approx(321.0)
    assert support_resistance["distance_from_support"] == pytest.approx((319.0 - 298.0) / 298.0)
    assert support_resistance["distance_from_resistance"] == pytest.approx((319.0 - 321.0) / 321.0)

    distances = sma_distances(candles)
    assert distances["distance_from_sma_20"] == pytest.approx((319.0 - 309.5) / 309.5)
    assert distances["distance_from_sma_50"] == pytest.approx((319.0 - 294.5) / 294.5)
    assert distances["distance_from_sma_200"] == pytest.approx((319.0 - 219.5) / 219.5)


def test_latest_candle_summary_accepts_lightweight_objects() -> None:
    candles = [
        CandleObject(
            date=date(2026, 1, index + 1),
            open=10.0 + index,
            high=12.0 + index,
            low=9.0 + index,
            close=11.0 + index,
            volume=1000 + index,
        )
        for index in range(3)
    ]

    summary = latest_candle_summary(candles)

    assert summary["date"] == "2026-01-03"
    assert summary["open"] == pytest.approx(12.0)
    assert summary["close"] == pytest.approx(13.0)
    assert summary["day_change"] == pytest.approx(1.0)
    assert summary["day_change_pct"] == pytest.approx(1.0 / 12.0)
    assert summary["range_pct"] == pytest.approx((14.0 - 11.0) / 11.0)
    assert summary["close_position_in_range"] == pytest.approx((13.0 - 11.0) / (14.0 - 11.0))


def test_build_technical_summary_rounds_values_and_classifies_trend() -> None:
    summary = build_technical_summary(_sample_candles())

    assert summary["latest_candle"]["date"] == "2025-08-08"
    assert summary["sma_20"] == pytest.approx(309.5)
    assert summary["sma_50"] == pytest.approx(294.5)
    assert summary["sma_200"] == pytest.approx(219.5)
    assert summary["rsi_14"] == pytest.approx(100.0)
    assert summary["atr_14"] == pytest.approx(4.0)
    assert summary["return_5d"] == pytest.approx(round((319.0 - 314.0) / 314.0, 4))
    assert summary["average_volume_20d"] == pytest.approx(3095.0)
    assert summary["latest_volume_vs_average_volume_20d"] == pytest.approx(round(3190.0 / 3095.0, 4))
    assert summary["relative_volume_1d"] == pytest.approx(round(3190.0 / 3095.0, 4))
    assert summary["relative_volume_5d"] == pytest.approx(round(3170.0 / 3095.0, 4))
    assert summary["up_day_volume_avg_20d"] == pytest.approx(3095.0)
    assert summary["down_day_volume_avg_20d"] is None
    assert summary["up_down_volume_ratio"] is None
    assert summary["volume_dry_up_near_support"] is False
    assert summary["breakout_volume_confirmed"] is False
    assert summary["distribution_days_20d"] == 0
    assert summary["accumulation_days_20d"] == 20
    assert summary["obv_trend"] == "up"
    assert summary["volume_price_confirmation"] == "confirmed"
    assert summary["high_20d"] == pytest.approx(321.0)
    assert summary["low_60d"] == pytest.approx(258.0)
    assert summary["20d_distance_from_resistance"] == pytest.approx(round((319.0 - 321.0) / 321.0, 4))
    assert summary["trend"] == "strong_uptrend"


def test_insufficient_history_returns_none_and_insufficient_trend() -> None:
    candles = _sample_candles(10)

    assert sma_20(candles) is None
    assert rsi_14(candles) is None
    assert atr_14(candles) is None
    assert return_over(candles, 20) is None
    assert average_volume(candles, 20) is None
    assert latest_volume_ratio(candles, 20) is None
    assert high_low(candles, 20) == {"high": None, "low": None}
    assert classify_trend(candles) == "insufficient_data"


def test_normalized_candle_dataclass_is_supported() -> None:
    candles = [
        NormalizedCandle(
            date=date(2025, 1, index + 1),
            open=20.0 + index,
            high=21.0 + index,
            low=19.0 + index,
            close=20.5 + index,
            volume=2000 + index,
        )
        for index in range(20)
    ]

    assert sma_20(candles) == pytest.approx(sum(20.5 + index for index in range(20)) / 20)
