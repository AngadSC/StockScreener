from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from app.utils.market_calendar import detect_missing_days, get_last_trading_day, get_trading_days_between


MIN_SWING_ANALYSIS_CANDLES = 60
RECENT_VOLUME_WINDOW = 20
RECENT_GAP_LOOKBACK_TRADING_DAYS = 20


@dataclass(frozen=True)
class OHLCVQualityConfig:
    min_swing_candles: int = MIN_SWING_ANALYSIS_CANDLES
    recent_volume_window: int = RECENT_VOLUME_WINDOW
    recent_gap_lookback_trading_days: int = RECENT_GAP_LOOKBACK_TRADING_DAYS


CandleLike = Mapping[str, Any] | Any


def _value(candle: CandleLike, field: str) -> Any:
    if isinstance(candle, Mapping):
        return candle.get(field)
    return getattr(candle, field, None)


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _date(candle: CandleLike) -> date | None:
    return _to_date(_value(candle, "date"))


def _date_string(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _ordered(candles: Sequence[CandleLike]) -> list[CandleLike]:
    return sorted(candles, key=lambda candle: _date(candle) or date.min)


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def assess_ohlcv_quality(
    candles: Sequence[CandleLike],
    *,
    as_of_date: date | datetime | str | None = None,
    expected_latest_date: date | datetime | str | None = None,
    config: OHLCVQualityConfig | None = None,
) -> dict[str, Any]:
    quality_config = config or OHLCVQualityConfig()
    ordered = _ordered(list(candles))
    initial_count = len(ordered)
    expected_latest = _to_date(expected_latest_date)
    if expected_latest is None:
        reference_date = _to_date(as_of_date) if as_of_date is not None else None
        expected_latest = get_last_trading_day(reference_date)

    reasons: list[str] = []
    warnings: list[str] = []
    invalid_dates: set[date] = set()
    missing_dates: list[date] = []

    if initial_count == 0:
        _append_reason(reasons, "no_candles")
        warnings.append("No OHLCV candles were provided.")
        return {
            "has_gaps": True,
            "reasons": reasons,
            "latest_db_date": None,
            "expected_latest_date": _date_string(expected_latest),
            "missing_dates": [],
            "invalid_candle_dates": [],
            "initial_candle_count": initial_count,
            "warnings": warnings,
        }

    if initial_count < quality_config.min_swing_candles:
        _append_reason(reasons, "insufficient_candles_for_swing_analysis")
        warnings.append(
            f"Only {initial_count} OHLCV candle(s) were provided; "
            f"{quality_config.min_swing_candles} are expected for swing analysis."
        )

    dated_candles: list[tuple[date, CandleLike]] = []
    for candle in ordered:
        candle_date = _date(candle)
        if candle_date is None:
            _append_reason(reasons, "invalid_candle_date")
            warnings.append("At least one OHLCV candle has a missing or invalid date.")
            continue
        dated_candles.append((candle_date, candle))

        null_fields = [
            field
            for field in ("open", "high", "low", "close", "volume")
            if _number(_value(candle, field)) is None
        ]
        if null_fields:
            invalid_dates.add(candle_date)

    if invalid_dates:
        _append_reason(reasons, "null_ohlcv_fields")
        warnings.append(f"{len(invalid_dates)} candle date(s) contain null or non-numeric OHLCV values.")

    latest_db_date = max((candle_date for candle_date, _candle in dated_candles), default=None)
    if latest_db_date is not None and latest_db_date < expected_latest:
        _append_reason(reasons, "latest_candle_stale")
        warnings.append(
            f"Latest DB candle is {latest_db_date.isoformat()}, "
            f"before expected latest trading day {expected_latest.isoformat()}."
        )

    if dated_candles:
        recent_for_volume = sorted(dated_candles, key=lambda item: item[0])[-quality_config.recent_volume_window :]
        bad_volume_dates = {
            candle_date
            for candle_date, candle in recent_for_volume
            if (_number(_value(candle, "volume")) is None or _number(_value(candle, "volume")) <= 0)
        }
        if bad_volume_dates:
            invalid_dates.update(bad_volume_dates)
            _append_reason(reasons, "invalid_recent_volume")
            warnings.append(
                f"{len(bad_volume_dates)} recent candle date(s) have zero, negative, or invalid volume."
            )

    if latest_db_date is not None:
        existing_dates = [candle_date for candle_date, _candle in dated_candles]
        earliest_db_date = min(existing_dates)
        recent_expected_days = get_trading_days_between(earliest_db_date, expected_latest)
        if len(recent_expected_days) > quality_config.recent_gap_lookback_trading_days:
            recent_expected_days = recent_expected_days[-quality_config.recent_gap_lookback_trading_days :]

        if recent_expected_days:
            missing_dates = detect_missing_days(
                existing_dates,
                recent_expected_days[0],
                recent_expected_days[-1],
            )

        if missing_dates:
            _append_reason(reasons, "missing_recent_trading_days")
            warnings.append(f"{len(missing_dates)} recent expected trading day(s) are missing from DB candles.")

    return {
        "has_gaps": bool(reasons),
        "reasons": reasons,
        "latest_db_date": _date_string(latest_db_date),
        "expected_latest_date": _date_string(expected_latest),
        "missing_dates": [_date_string(missing_date) for missing_date in missing_dates],
        "invalid_candle_dates": [_date_string(invalid_date) for invalid_date in sorted(invalid_dates)],
        "initial_candle_count": initial_count,
        "warnings": warnings,
    }


def build_ohlcv_quality_metadata(
    candles: Sequence[CandleLike],
    *,
    as_of_date: date | datetime | str | None = None,
    expected_latest_date: date | datetime | str | None = None,
    config: OHLCVQualityConfig | None = None,
) -> dict[str, Any]:
    return assess_ohlcv_quality(
        candles,
        as_of_date=as_of_date,
        expected_latest_date=expected_latest_date,
        config=config,
    )
