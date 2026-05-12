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


def relative_volume(candles: Sequence[CandleLike], recent_window: int, baseline_window: int = 20) -> float | None:
    ordered = _ordered(candles)
    if recent_window <= 0 or baseline_window <= 0 or len(ordered) < max(recent_window, baseline_window):
        return None

    recent_volumes = [_number(candle, "volume") for candle in ordered[-recent_window:]]
    if any(volume is None for volume in recent_volumes):
        return None

    baseline = average_volume(ordered, baseline_window)
    if baseline in (None, 0):
        return None

    return sum(volume for volume in recent_volumes if volume is not None) / recent_window / baseline


def _recent_price_volume_pairs(
    candles: Sequence[CandleLike], window: int = 20
) -> list[tuple[CandleLike, CandleLike]]:
    ordered = _ordered(candles)
    if window <= 0 or len(ordered) < 2:
        return []

    start_index = max(1, len(ordered) - window)
    return [(ordered[index - 1], ordered[index]) for index in range(start_index, len(ordered))]


def up_down_volume_averages(candles: Sequence[CandleLike], window: int = 20) -> dict[str, float | None]:
    up_day_volumes: list[float] = []
    down_day_volumes: list[float] = []

    for previous, current in _recent_price_volume_pairs(candles, window):
        previous_close = _number(previous, "close")
        current_close = _number(current, "close")
        current_volume = _number(current, "volume")
        if previous_close is None or current_close is None or current_volume is None:
            continue
        if current_close > previous_close:
            up_day_volumes.append(current_volume)
        elif current_close < previous_close:
            down_day_volumes.append(current_volume)

    up_average = sum(up_day_volumes) / len(up_day_volumes) if up_day_volumes else None
    down_average = sum(down_day_volumes) / len(down_day_volumes) if down_day_volumes else None
    ratio = None
    if up_average is not None and down_average not in (None, 0):
        ratio = up_average / down_average

    return {
        "up_day_volume_avg_20d": up_average,
        "down_day_volume_avg_20d": down_average,
        "up_down_volume_ratio": ratio,
    }


def volume_dry_up_near_support(candles: Sequence[CandleLike]) -> bool:
    ordered = _ordered(candles)
    if len(ordered) < 20:
        return False

    latest_close = _latest_close(ordered)
    support = high_low(ordered, 20)["low"]
    relative_volume_5d = relative_volume(ordered, 5, 20)
    if latest_close is None or support in (None, 0) or relative_volume_5d is None:
        return False

    distance_from_support = (latest_close - support) / support
    return 0 <= distance_from_support <= 0.03 and relative_volume_5d <= 0.75


def breakout_volume_confirmed(candles: Sequence[CandleLike]) -> bool:
    ordered = _ordered(candles)
    if len(ordered) < 21:
        return False

    latest_close = _number(ordered[-1], "close")
    prior_highs = [_number(candle, "high") for candle in ordered[-21:-1]]
    relative_volume_1d = relative_volume(ordered, 1, 20)
    if latest_close is None or any(high is None for high in prior_highs) or relative_volume_1d is None:
        return False

    prior_resistance = max(high for high in prior_highs if high is not None)
    return latest_close > prior_resistance and relative_volume_1d >= 1.5


def distribution_days(candles: Sequence[CandleLike], window: int = 20) -> int | None:
    pairs = _recent_price_volume_pairs(candles, window)
    if not pairs:
        return None

    count = 0
    for previous, current in pairs:
        previous_close = _number(previous, "close")
        current_close = _number(current, "close")
        previous_volume = _number(previous, "volume")
        current_volume = _number(current, "volume")
        if (
            previous_close in (None, 0)
            or current_close is None
            or previous_volume is None
            or current_volume is None
        ):
            continue
        change = (current_close - previous_close) / previous_close
        if change <= -0.002 and current_volume > previous_volume:
            count += 1
    return count


def accumulation_days(candles: Sequence[CandleLike], window: int = 20) -> int | None:
    pairs = _recent_price_volume_pairs(candles, window)
    if not pairs:
        return None

    count = 0
    for previous, current in pairs:
        previous_close = _number(previous, "close")
        current_close = _number(current, "close")
        previous_volume = _number(previous, "volume")
        current_volume = _number(current, "volume")
        if (
            previous_close in (None, 0)
            or current_close is None
            or previous_volume is None
            or current_volume is None
        ):
            continue
        change = (current_close - previous_close) / previous_close
        if change >= 0.002 and current_volume > previous_volume:
            count += 1
    return count


def obv_trend(candles: Sequence[CandleLike], window: int = 20) -> str:
    ordered = _ordered(candles)
    if len(ordered) < 2:
        return "flat"

    obv_values = [0.0]
    for previous, current in zip(ordered, ordered[1:]):
        previous_close = _number(previous, "close")
        current_close = _number(current, "close")
        current_volume = _number(current, "volume")
        if previous_close is None or current_close is None or current_volume is None:
            return "flat"
        if current_close > previous_close:
            obv_values.append(obv_values[-1] + current_volume)
        elif current_close < previous_close:
            obv_values.append(obv_values[-1] - current_volume)
        else:
            obv_values.append(obv_values[-1])

    lookback = min(window, len(obv_values) - 1)
    recent_volumes = [_number(candle, "volume") for candle in ordered[-lookback:]]
    if not recent_volumes or any(volume is None for volume in recent_volumes):
        return "flat"

    net_obv_change = obv_values[-1] - obv_values[-(lookback + 1)]
    average_recent_volume = sum(volume for volume in recent_volumes if volume is not None) / lookback
    threshold = average_recent_volume * 1.5
    if net_obv_change > threshold:
        return "up"
    if net_obv_change < -threshold:
        return "down"
    return "flat"


def volume_price_confirmation(candles: Sequence[CandleLike]) -> str:
    price_return = return_over(candles, 20)
    if price_return is None:
        price_return = return_over(candles, 10)
    trend = obv_trend(candles)

    if price_return is None or abs(price_return) < 0.02 or trend == "flat":
        return "neutral"
    if price_return > 0 and trend == "up":
        return "confirmed"
    if price_return < 0 and trend == "down":
        return "confirmed"
    return "divergent"


def volume_intelligence(candles: Sequence[CandleLike]) -> dict[str, Any]:
    up_down = up_down_volume_averages(candles, 20)
    return {
        "relative_volume_1d": relative_volume(candles, 1, 20),
        "relative_volume_5d": relative_volume(candles, 5, 20),
        **up_down,
        "volume_dry_up_near_support": volume_dry_up_near_support(candles),
        "breakout_volume_confirmed": breakout_volume_confirmed(candles),
        "distribution_days_20d": distribution_days(candles, 20),
        "accumulation_days_20d": accumulation_days(candles, 20),
        "obv_trend": obv_trend(candles),
        "volume_price_confirmation": volume_price_confirmation(candles),
    }


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


def _percent_distance_to_support(candles: Sequence[CandleLike], support: float | None) -> float | None:
    latest_close = _latest_close(candles)
    if latest_close in (None, 0) or support is None:
        return None
    return (latest_close - support) / latest_close * 100


def _percent_distance_to_resistance(candles: Sequence[CandleLike], resistance: float | None) -> float | None:
    latest_close = _latest_close(candles)
    if latest_close in (None, 0) or resistance is None:
        return None
    return (resistance - latest_close) / latest_close * 100


def _within_pct_below(value: float | None, level: float | None, threshold_pct: float) -> bool:
    if value in (None, 0) or level in (None, 0):
        return False
    return value <= level and ((level - value) / level * 100) <= threshold_pct


def _window_range_pct(candles: Sequence[CandleLike], window: int) -> float | None:
    ordered = _ordered(candles)
    if window <= 0 or len(ordered) < window:
        return None
    highs = [_number(candle, "high") for candle in ordered[-window:]]
    lows = [_number(candle, "low") for candle in ordered[-window:]]
    if any(high is None for high in highs) or any(low is None for low in lows):
        return None
    high = max(high for high in highs if high is not None)
    low = min(low for low in lows if low is not None)
    if low == 0:
        return None
    return (high - low) / low * 100


def _range_compression(candles: Sequence[CandleLike]) -> tuple[bool, str]:
    recent_range = _window_range_pct(candles, 10)
    medium_range = _window_range_pct(candles, 20)
    larger_range = _window_range_pct(candles, 60)
    if recent_range is None or medium_range is None:
        return False, "insufficient_data"
    if recent_range <= medium_range * 0.7 and (larger_range is None or recent_range <= larger_range * 0.45):
        return True, "compressed_range"
    if larger_range is not None and recent_range >= larger_range * 0.85:
        return False, "wide_range"
    return False, "normal_range"


def _segment_high_low(candles: Sequence[CandleLike], start: int, end: int) -> tuple[float | None, float | None]:
    segment = _ordered(candles)[start:end]
    if not segment:
        return None, None
    highs = [_number(candle, "high") for candle in segment]
    lows = [_number(candle, "low") for candle in segment]
    if any(high is None for high in highs) or any(low is None for low in lows):
        return None, None
    return max(high for high in highs if high is not None), min(low for low in lows if low is not None)


def _higher_or_lower_structure(candles: Sequence[CandleLike]) -> tuple[bool, bool]:
    ordered = _ordered(candles)
    if len(ordered) < 30:
        return False, False

    segments = [
        _segment_high_low(ordered, -30, -20),
        _segment_high_low(ordered, -20, -10),
        _segment_high_low(ordered, -10, len(ordered)),
    ]
    highs = [segment[0] for segment in segments]
    lows = [segment[1] for segment in segments]
    if any(value is None for value in [*highs, *lows]):
        return False, False

    numeric_highs = [value for value in highs if value is not None]
    numeric_lows = [value for value in lows if value is not None]
    higher = numeric_highs[0] < numeric_highs[1] < numeric_highs[2] and numeric_lows[0] < numeric_lows[1] < numeric_lows[2]
    lower = numeric_highs[0] > numeric_highs[1] > numeric_highs[2] and numeric_lows[0] > numeric_lows[1] > numeric_lows[2]
    return higher, lower


def _recent_gap_flags(candles: Sequence[CandleLike], window: int = 5) -> tuple[bool, bool]:
    ordered = _ordered(candles)
    if len(ordered) < 2:
        return False, False

    gap_up = False
    gap_down = False
    start_index = max(1, len(ordered) - window)
    for index in range(start_index, len(ordered)):
        open_price = _number(ordered[index], "open")
        previous_high = _number(ordered[index - 1], "high")
        previous_low = _number(ordered[index - 1], "low")
        if open_price is None or previous_high is None or previous_low is None:
            continue
        gap_up = gap_up or open_price >= previous_high * 1.01
        gap_down = gap_down or open_price <= previous_low * 0.99
    return gap_up, gap_down


def _prior_resistance(candles: Sequence[CandleLike], window: int = 20) -> float | None:
    ordered = _ordered(candles)
    if len(ordered) <= window:
        return None
    prior = ordered[-(window + 1) : -1]
    highs = [_number(candle, "high") for candle in prior]
    if any(high is None for high in highs):
        return None
    return max(high for high in highs if high is not None)


def _failed_breakout(candles: Sequence[CandleLike], window: int = 10, resistance_window: int = 20) -> bool:
    ordered = _ordered(candles)
    latest_close = _latest_close(ordered)
    if len(ordered) <= resistance_window + 1 or latest_close is None:
        return False

    start_index = max(resistance_window, len(ordered) - window)
    for index in range(start_index, len(ordered)):
        prior = ordered[index - resistance_window : index]
        prior_highs = [_number(candle, "high") for candle in prior]
        close = _number(ordered[index], "close")
        if close is None or any(high is None for high in prior_highs):
            continue
        resistance = max(high for high in prior_highs if high is not None)
        if close > resistance * 1.005 and latest_close < resistance:
            return True
    return False


def _pullback_to_sma(candles: Sequence[CandleLike], moving_average: float | None, threshold_pct: float = 2.0) -> bool:
    if moving_average in (None, 0):
        return False
    ordered = _ordered(candles)
    if not ordered:
        return False
    latest = ordered[-1]
    latest_low = _number(latest, "low")
    latest_close = _number(latest, "close")
    if latest_low is None or latest_close is None:
        return False
    touched_average = latest_low <= moving_average * (1 + threshold_pct / 100)
    closed_above = latest_close >= moving_average * (1 - threshold_pct / 100)
    return touched_average and closed_above


def price_action_structure(candles: Sequence[CandleLike]) -> dict[str, Any]:
    ordered = _ordered(candles)
    latest_close = _latest_close(ordered)
    latest_high = _number(ordered[-1], "high") if ordered else None
    high_low_20d = high_low(ordered, 20)
    high_low_60d = high_low(ordered, 60)
    support = high_low_20d["low"]
    resistance = _prior_resistance(ordered, 20) or high_low_20d["high"]
    prior_resistance = _prior_resistance(ordered, 20)
    sma20 = sma_20(ordered)
    sma50 = sma_50(ordered)
    sma200 = sma_200(ordered)

    range_compressed, range_label = _range_compression(ordered)
    higher_structure, lower_structure = _higher_or_lower_structure(ordered)
    gap_up, gap_down = _recent_gap_flags(ordered, 5)
    failed_breakout = _failed_breakout(ordered)
    breakout_confirmed = breakout_volume_confirmed(ordered)
    breakout_attempt = bool(
        prior_resistance
        and latest_close is not None
        and latest_high is not None
        and not breakout_confirmed
        and not failed_breakout
        and (latest_high >= prior_resistance * 0.995 or _within_pct_below(latest_close, prior_resistance, 2.0))
    )
    pullback20 = _pullback_to_sma(ordered, sma20)
    pullback50 = _pullback_to_sma(ordered, sma50)

    labels: list[str] = []
    if higher_structure:
        labels.append("higher_highs_higher_lows")
    if lower_structure:
        labels.append("lower_highs_lower_lows")
    if range_compressed:
        labels.append("range_compression")
    if breakout_confirmed:
        labels.append("confirmed_breakout")
    elif failed_breakout:
        labels.append("failed_breakout")
    elif breakout_attempt:
        labels.append("breakout_attempt")
    if pullback20:
        labels.append("pullback_to_sma20")
    if pullback50:
        labels.append("pullback_to_sma50")
    if gap_up:
        labels.append("recent_gap_up")
    if gap_down:
        labels.append("recent_gap_down")

    if breakout_confirmed:
        breakout_label = "confirmed_breakout"
    elif failed_breakout:
        breakout_label = "failed_breakout"
    elif breakout_attempt:
        breakout_label = "breakout_attempt"
    elif _within_pct_below(latest_close, prior_resistance, 3.0):
        breakout_label = "near_resistance"
    else:
        breakout_label = "no_breakout_setup" if len(ordered) >= 21 else "insufficient_data"

    if higher_structure:
        structure_label = "higher_highs_higher_lows"
    elif lower_structure:
        structure_label = "lower_highs_lower_lows"
    elif range_compressed:
        structure_label = "range_compression"
    elif len(ordered) >= 30:
        structure_label = "sideways_or_mixed"
    else:
        structure_label = "insufficient_data"

    if pullback20:
        pullback_label = "pullback_to_sma20"
    elif pullback50:
        pullback_label = "pullback_to_sma50"
    elif latest_close is not None and sma20 not in (None, 0) and latest_close > sma20 * 1.08:
        pullback_label = "extended_above_sma20"
    elif latest_close is not None and sma50 is not None and latest_close < sma50:
        pullback_label = "below_key_sma"
    else:
        pullback_label = "no_clear_pullback" if len(ordered) >= 50 else "insufficient_data"

    if failed_breakout:
        setup_label = "failed_breakout"
    elif breakout_confirmed:
        setup_label = "confirmed_breakout"
    elif breakout_attempt and range_compressed:
        setup_label = "compression_breakout_attempt"
    elif breakout_attempt:
        setup_label = "breakout_attempt"
    elif higher_structure and (pullback20 or pullback50):
        setup_label = "trend_pullback"
    elif lower_structure:
        setup_label = "downtrend_structure"
    elif range_compressed:
        setup_label = "base_compression"
    else:
        setup_label = "no_clear_setup" if len(ordered) >= 30 else "insufficient_data"

    return {
        "setup_label": setup_label,
        "structure_label": structure_label,
        "breakout_label": breakout_label,
        "pullback_label": pullback_label,
        "range_label": range_label,
        "gap_label": "recent_gap_up" if gap_up else "recent_gap_down" if gap_down else "no_recent_gap",
        "labels": labels or [setup_label],
        "near_20d_high": _within_pct_below(latest_close, high_low_20d["high"], 3.0),
        "near_60d_high": _within_pct_below(latest_close, high_low_60d["high"], 3.0),
        "distance_to_support_pct": _percent_distance_to_support(ordered, support),
        "distance_to_resistance_pct": _percent_distance_to_resistance(ordered, resistance),
        "range_compression": range_compressed,
        "higher_highs_higher_lows": higher_structure,
        "lower_highs_lower_lows": lower_structure,
        "gap_up_recent": gap_up,
        "gap_down_recent": gap_down,
        "failed_breakout": failed_breakout,
        "breakout_attempt": breakout_attempt,
        "pullback_to_sma20": pullback20,
        "pullback_to_sma50": pullback50,
        "support_level": support,
        "resistance_level": resistance,
        "prior_20d_resistance": prior_resistance,
        "sma_20": sma20,
        "sma_50": sma50,
        "sma_200": sma200,
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
    volume_signals = volume_intelligence(candles)
    levels = high_lows(candles)
    support_resistance_20d = support_resistance_distances(candles, 20)
    structure = price_action_structure(candles)

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
        **{
            key: _round(value) if isinstance(value, (float, int)) and not isinstance(value, bool) else value
            for key, value in volume_signals.items()
        },
        **{key: _round(value) for key, value in levels.items()},
        **{f"20d_{key}": _round(value) for key, value in support_resistance_20d.items()},
        **{key: _round(value) for key, value in sma_distances(candles).items()},
        "price_action_structure": {
            key: _round(value) if isinstance(value, (float, int)) and not isinstance(value, bool) else value
            for key, value in structure.items()
        },
        "trend": classify_trend(candles),
    }
