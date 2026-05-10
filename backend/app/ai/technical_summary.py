from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class NormalizedCandle:
    date: date | datetime | str
    open: float
    high: float
    low: float
    close: float
    volume: int | float


CandleLike = Mapping[str, Any] | Any


def _value(candle: CandleLike, field: str) -> Any:
    if isinstance(candle, Mapping):
        return candle.get(field)
    return getattr(candle, field, None)


def _number(candle: CandleLike, field: str) -> float | None:
    value = _value(candle, field)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _date_key(candle: CandleLike) -> str:
    value = _value(candle, "date")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "")


def _ordered(candles: Sequence[CandleLike]) -> list[CandleLike]:
    return sorted(candles, key=_date_key)


def _latest_close(candles: Sequence[CandleLike]) -> float | None:
    ordered = _ordered(candles)
    if not ordered:
        return None
    return _number(ordered[-1], "close")


def _round(value: float | int | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _percent_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous


def sma(candles: Sequence[CandleLike], window: int) -> float | None:
    ordered = _ordered(candles)
    if window <= 0 or len(ordered) < window:
        return None
    closes = [_number(candle, "close") for candle in ordered[-window:]]
    if any(close is None for close in closes):
        return None
    return sum(close for close in closes if close is not None) / window


def sma_20(candles: Sequence[CandleLike]) -> float | None:
    return sma(candles, 20)


def sma_50(candles: Sequence[CandleLike]) -> float | None:
    return sma(candles, 50)


def sma_200(candles: Sequence[CandleLike]) -> float | None:
    return sma(candles, 200)


def rsi_14(candles: Sequence[CandleLike]) -> float | None:
    ordered = _ordered(candles)
    period = 14
    if len(ordered) <= period:
        return None

    closes = [_number(candle, "close") for candle in ordered]
    if any(close is None for close in closes):
        return None

    gains: list[float] = []
    losses: list[float] = []
    numeric_closes = [close for close in closes if close is not None]
    for previous, current in zip(numeric_closes[-(period + 1) :], numeric_closes[-period:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def atr_14(candles: Sequence[CandleLike]) -> float | None:
    ordered = _ordered(candles)
    period = 14
    if len(ordered) <= period:
        return None

    true_ranges: list[float] = []
    start = len(ordered) - period
    for index in range(start, len(ordered)):
        high = _number(ordered[index], "high")
        low = _number(ordered[index], "low")
        previous_close = _number(ordered[index - 1], "close")
        if high is None or low is None or previous_close is None:
            return None
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))

    return sum(true_ranges) / period


def return_over(candles: Sequence[CandleLike], days: int) -> float | None:
    ordered = _ordered(candles)
    if days <= 0 or len(ordered) <= days:
        return None
    current = _number(ordered[-1], "close")
    previous = _number(ordered[-(days + 1)], "close")
    return _percent_change(current, previous)


def returns(candles: Sequence[CandleLike]) -> dict[str, float | None]:
    return {
        "return_5d": return_over(candles, 5),
        "return_10d": return_over(candles, 10),
        "return_20d": return_over(candles, 20),
        "return_60d": return_over(candles, 60),
    }


def average_volume(candles: Sequence[CandleLike], window: int) -> float | None:
    ordered = _ordered(candles)
    if window <= 0 or len(ordered) < window:
        return None
    volumes = [_number(candle, "volume") for candle in ordered[-window:]]
    if any(volume is None for volume in volumes):
        return None
    return sum(volume for volume in volumes if volume is not None) / window


def average_volumes(candles: Sequence[CandleLike]) -> dict[str, float | None]:
    return {
        "average_volume_20d": average_volume(candles, 20),
        "average_volume_30d": average_volume(candles, 30),
        "average_volume_50d": average_volume(candles, 50),
    }


def latest_volume_ratio(candles: Sequence[CandleLike], window: int = 20) -> float | None:
    ordered = _ordered(candles)
    if not ordered:
        return None
    latest_volume = _number(ordered[-1], "volume")
    baseline = average_volume(ordered, window)
    if latest_volume is None or baseline in (None, 0):
        return None
    return latest_volume / baseline


def high_low(candles: Sequence[CandleLike], window: int) -> dict[str, float | None]:
    ordered = _ordered(candles)
    if window <= 0 or len(ordered) < window:
        return {"high": None, "low": None}
    highs = [_number(candle, "high") for candle in ordered[-window:]]
    lows = [_number(candle, "low") for candle in ordered[-window:]]
    if any(high is None for high in highs) or any(low is None for low in lows):
        return {"high": None, "low": None}
    return {
        "high": max(high for high in highs if high is not None),
        "low": min(low for low in lows if low is not None),
    }


def high_lows(candles: Sequence[CandleLike]) -> dict[str, float | None]:
    high_low_20d = high_low(candles, 20)
    high_low_60d = high_low(candles, 60)
    return {
        "high_20d": high_low_20d["high"],
        "low_20d": high_low_20d["low"],
        "high_60d": high_low_60d["high"],
        "low_60d": high_low_60d["low"],
    }


def distance_from_level(candles: Sequence[CandleLike], level: float | None) -> float | None:
    latest_close = _latest_close(candles)
    if latest_close is None or level in (None, 0):
        return None
    return (latest_close - level) / level


def support_resistance_distances(
    candles: Sequence[CandleLike], window: int = 20
) -> dict[str, float | None]:
    levels = high_low(candles, window)
    support = levels["low"]
    resistance = levels["high"]
    return {
        "support": support,
        "resistance": resistance,
        "distance_from_support": distance_from_level(candles, support),
        "distance_from_resistance": distance_from_level(candles, resistance),
    }


def sma_distances(candles: Sequence[CandleLike]) -> dict[str, float | None]:
    sma20 = sma_20(candles)
    sma50 = sma_50(candles)
    sma200 = sma_200(candles)
    return {
        "distance_from_sma_20": distance_from_level(candles, sma20),
        "distance_from_sma_50": distance_from_level(candles, sma50),
        "distance_from_sma_200": distance_from_level(candles, sma200),
    }


def latest_candle_summary(candles: Sequence[CandleLike]) -> dict[str, Any]:
    ordered = _ordered(candles)
    if not ordered:
        return {
            "date": None,
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "day_change": None,
            "day_change_pct": None,
            "range_pct": None,
            "close_position_in_range": None,
        }

    latest = ordered[-1]
    open_price = _number(latest, "open")
    high = _number(latest, "high")
    low = _number(latest, "low")
    close = _number(latest, "close")
    volume = _number(latest, "volume")
    day_change = None if open_price is None or close is None else close - open_price
    range_pct = _percent_change(high, low)
    close_position = None
    if close is not None and high is not None and low is not None and high != low:
        close_position = (close - low) / (high - low)

    return {
        "date": _date_key(latest),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "day_change": day_change,
        "day_change_pct": _percent_change(close, open_price),
        "range_pct": range_pct,
        "close_position_in_range": close_position,
    }


def classify_trend(candles: Sequence[CandleLike]) -> str:
    latest_close = _latest_close(candles)
    sma20 = sma_20(candles)
    sma50 = sma_50(candles)
    sma200 = sma_200(candles)
    return20 = return_over(candles, 20)
    return60 = return_over(candles, 60)

    if latest_close is None or sma20 is None or sma50 is None:
        return "insufficient_data"

    above_20_50 = latest_close > sma20 > sma50
    below_20_50 = latest_close < sma20 < sma50

    if sma200 is not None:
        if above_20_50 and sma50 > sma200 and return60 is not None and return60 > 0.08:
            return "strong_uptrend"
        if below_20_50 and sma50 < sma200 and return60 is not None and return60 < -0.08:
            return "strong_downtrend"

    if above_20_50 and return20 is not None and return20 > 0:
        return "uptrend"
    if below_20_50 and return20 is not None and return20 < 0:
        return "downtrend"
    return "sideways"


def build_technical_summary(candles: Sequence[CandleLike]) -> dict[str, Any]:
    sma20 = sma_20(candles)
    sma50 = sma_50(candles)
    sma200 = sma_200(candles)
    volume_averages = average_volumes(candles)
    levels = high_lows(candles)
    support_resistance_20d = support_resistance_distances(candles, 20)

    return {
        "latest_candle": {key: _round(value) if isinstance(value, (float, int)) else value for key, value in latest_candle_summary(candles).items()},
        "sma_20": _round(sma20),
        "sma_50": _round(sma50),
        "sma_200": _round(sma200),
        "rsi_14": _round(rsi_14(candles)),
        "atr_14": _round(atr_14(candles)),
        **{key: _round(value) for key, value in returns(candles).items()},
        **{key: _round(value) for key, value in volume_averages.items()},
        "latest_volume_vs_average_volume_20d": _round(latest_volume_ratio(candles, 20)),
        **{key: _round(value) for key, value in levels.items()},
        **{f"20d_{key}": _round(value) for key, value in support_resistance_20d.items()},
        **{key: _round(value) for key, value in sma_distances(candles).items()},
        "trend": classify_trend(candles),
    }
