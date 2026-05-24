"""
Deterministic trade-level calculator.

Computes exact actionable price levels from the technical_summary dict produced
by build_technical_summary() / _technical_summary() in payload_builder.py.

The function never raises — every failure path degrades gracefully to None +
a warning string so the caller can always use the return value safely.
"""
from __future__ import annotations

from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TradeLevelsResult(TypedDict):
    current_price: float | None
    preferred_entry: float | None
    aggressive_entry_min: float | None
    aggressive_entry_max: float | None
    confirmation_trigger: float | None
    add_level: float | None
    invalidation_level: float | None
    target_1: float | None
    target_2: float | None
    chase_above: float | None
    method: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _round_price(price: float) -> float:
    """Round to 3 decimal places for sub-$5 stocks, 2 decimal places otherwise."""
    if price < 5:
        return round(price, 3)
    return round(price, 2)


def _safe_float(value: Any) -> float | None:
    """Convert an arbitrary value to float, returning None on failure or NaN."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:  # NaN check
        return None
    return numeric


def _safe_bool(value: Any) -> bool:
    """Return a bool from an arbitrary value without raising."""
    if isinstance(value, bool):
        return value
    return bool(value)


def _atr_or_proxy(atr: float | None, current_price: float | None, warnings: list[str]) -> float | None:
    """
    Return ATR if valid (> 0), otherwise fall back to 3% of current_price.
    Appends a warning when the proxy is used.
    Returns None only when both ATR and current_price are unavailable.
    """
    if atr is not None and atr > 0:
        return atr
    if current_price is not None and current_price > 0:
        warnings.append("ATR unavailable, using 3% price proxy")
        return current_price * 0.03
    return None


def _rp(value: float | None) -> float | None:
    """Apply _round_price only when value is not None."""
    if value is None:
        return None
    return _round_price(value)


# ---------------------------------------------------------------------------
# Method builders
# ---------------------------------------------------------------------------

def _build_breakout(
    current_price: float,
    atr: float,
    resistance_level: float | None,
    support_level: float | None,
    sma_20: float | None,
    warnings: list[str],
) -> dict[str, Any]:
    if resistance_level is None:
        warnings.append("resistance_level unavailable; confirmation_trigger estimated from current price")

    confirmation_trigger = (
        _rp(resistance_level + 0.15 * atr)
        if resistance_level is not None
        else _rp(current_price + 0.15 * atr)
    )
    preferred_entry = confirmation_trigger

    if sma_20 is not None and support_level is not None:
        aggressive_entry_min = _rp(max(sma_20, support_level))
    elif sma_20 is not None:
        aggressive_entry_min = _rp(sma_20)
    elif support_level is not None:
        aggressive_entry_min = _rp(support_level)
    else:
        aggressive_entry_min = None
        warnings.append("support_level and sma_20 unavailable; aggressive_entry_min not calculated")

    aggressive_entry_max = _rp(current_price)

    if support_level is not None:
        invalidation_level = _rp(support_level - 0.20 * atr)
    else:
        invalidation_level = _rp(current_price - 1.5 * atr)
        if support_level is None:
            warnings.append("support_level unavailable; invalidation estimated from current price - 1.5 ATR")

    entry_base = preferred_entry if preferred_entry is not None else current_price
    target_1 = _rp(entry_base + 1.0 * atr)
    target_2 = _rp(entry_base + 2.0 * atr)
    add_level = target_1
    chase_above = _rp(entry_base + 1.25 * atr)

    return {
        "preferred_entry": preferred_entry,
        "aggressive_entry_min": aggressive_entry_min,
        "aggressive_entry_max": aggressive_entry_max,
        "confirmation_trigger": confirmation_trigger,
        "add_level": add_level,
        "invalidation_level": invalidation_level,
        "target_1": target_1,
        "target_2": target_2,
        "chase_above": chase_above,
    }


def _build_pullback(
    current_price: float,
    atr: float,
    resistance_level: float | None,
    support_level: float | None,
    sma_20: float | None,
    sma_50: float | None,
    high_20d: float | None,
    pullback_to_sma20: bool,
    pullback_to_sma50: bool,
    warnings: list[str],
) -> dict[str, Any]:
    # preferred_entry
    if pullback_to_sma20 and sma_20 is not None:
        preferred_entry = _rp(sma_20)
    elif pullback_to_sma50 and sma_50 is not None:
        preferred_entry = _rp(sma_50)
    elif support_level is not None:
        preferred_entry = _rp(support_level)
    else:
        preferred_entry = _rp(current_price)
        warnings.append("No sma_20/sma_50/support available for preferred_entry; using current price")

    # aggressive zone
    if sma_20 is not None and support_level is not None:
        aggressive_entry_min = _rp(min(sma_20, support_level))
    elif sma_20 is not None:
        aggressive_entry_min = _rp(sma_20)
    elif support_level is not None:
        aggressive_entry_min = _rp(support_level)
    else:
        aggressive_entry_min = None
        warnings.append("support_level and sma_20 unavailable; aggressive_entry_min not calculated")

    if sma_20 is not None:
        aggressive_entry_max = _rp(max(sma_20, current_price * 0.99))
    else:
        aggressive_entry_max = _rp(current_price * 0.99)

    # confirmation trigger
    if resistance_level is not None:
        confirmation_trigger = _rp(resistance_level)
    elif high_20d is not None:
        confirmation_trigger = _rp(high_20d)
    else:
        confirmation_trigger = None
        warnings.append("resistance_level and high_20d unavailable; confirmation_trigger not calculated")

    # invalidation
    if sma_50 is not None:
        invalidation_level = _rp(sma_50 - 0.20 * atr)
    elif support_level is not None:
        invalidation_level = _rp(support_level - 0.30 * atr)
    else:
        invalidation_level = _rp(current_price - 1.5 * atr)
        warnings.append("sma_50 and support_level unavailable; invalidation estimated from current price - 1.5 ATR")

    entry_base = preferred_entry if preferred_entry is not None else current_price
    target_1 = _rp(entry_base + 1.0 * atr)

    if (
        resistance_level is not None
        and resistance_level > (target_1 if target_1 is not None else 0)
    ):
        target_2 = _rp(resistance_level)
    else:
        target_2 = _rp(entry_base + 2.0 * atr)

    add_level = target_1
    chase_above = _rp(entry_base + 1.5 * atr)

    return {
        "preferred_entry": preferred_entry,
        "aggressive_entry_min": aggressive_entry_min,
        "aggressive_entry_max": aggressive_entry_max,
        "confirmation_trigger": confirmation_trigger,
        "add_level": add_level,
        "invalidation_level": invalidation_level,
        "target_1": target_1,
        "target_2": target_2,
        "chase_above": chase_above,
    }


def _build_breakdown(
    current_price: float,
    atr: float,
    resistance_level: float | None,
    support_level: float | None,
    warnings: list[str],
) -> dict[str, Any]:
    if support_level is None:
        warnings.append("support_level unavailable; confirmation_trigger estimated from current price")

    confirmation_trigger = (
        _rp(support_level - 0.15 * atr)
        if support_level is not None
        else _rp(current_price - 0.15 * atr)
    )
    preferred_entry = confirmation_trigger

    aggressive_entry_min = _rp(current_price)

    if resistance_level is not None:
        aggressive_entry_max = _rp(resistance_level)
    else:
        aggressive_entry_max = _rp(current_price * 1.02)
        warnings.append("resistance_level unavailable; aggressive_entry_max estimated at current price + 2%")

    if resistance_level is not None:
        invalidation_level = _rp(resistance_level + 0.20 * atr)
    else:
        invalidation_level = _rp(current_price + 1.5 * atr)
        if resistance_level is None:
            warnings.append("resistance_level unavailable; invalidation estimated from current price + 1.5 ATR")

    entry_base = preferred_entry if preferred_entry is not None else current_price
    target_1 = _rp(entry_base - 1.0 * atr)
    target_2 = _rp(entry_base - 2.0 * atr)
    add_level = target_1
    chase_above = None  # no chase level for breakdown shorts

    return {
        "preferred_entry": preferred_entry,
        "aggressive_entry_min": aggressive_entry_min,
        "aggressive_entry_max": aggressive_entry_max,
        "confirmation_trigger": confirmation_trigger,
        "add_level": add_level,
        "invalidation_level": invalidation_level,
        "target_1": target_1,
        "target_2": target_2,
        "chase_above": chase_above,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_trade_levels(
    technical_summary: dict[str, Any],
    scoring_data: dict[str, Any],  # noqa: ARG001  (available for future use)
) -> TradeLevelsResult:
    """
    Compute deterministic trade-level prices from technical_summary data.

    Args:
        technical_summary: The dict returned by _technical_summary() in
                           payload_builder.py.
        scoring_data:      The deterministic_scores dict (reserved for future
                           use; not consumed here to keep calculations pure).

    Returns:
        A TradeLevelsResult TypedDict with all price levels rounded
        appropriately, a method string, and a warnings list.
    """
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Extract top-level technical fields
    # ------------------------------------------------------------------
    latest_candle = technical_summary.get("latest_candle") or {}
    current_price = _safe_float(latest_candle.get("close"))
    atr_raw = _safe_float(technical_summary.get("atr_14"))
    sma_20_val = _safe_float(technical_summary.get("sma_20"))
    sma_50_val = _safe_float(technical_summary.get("sma_50"))
    trend = str(technical_summary.get("trend") or "")

    price_levels = technical_summary.get("price_levels") or {}
    high_20d = _safe_float(price_levels.get("high_20d"))

    price_action = technical_summary.get("price_action_structure") or {}
    support_level = _safe_float(price_action.get("support_level"))
    resistance_level = _safe_float(price_action.get("resistance_level"))
    breakout_label = str(price_action.get("breakout_label") or "")
    breakout_attempt = _safe_bool(price_action.get("breakout_attempt"))
    pullback_to_sma20 = _safe_bool(price_action.get("pullback_to_sma20"))
    pullback_to_sma50 = _safe_bool(price_action.get("pullback_to_sma50"))
    higher_highs = _safe_bool(price_action.get("higher_highs_higher_lows"))
    lower_highs = _safe_bool(price_action.get("lower_highs_lower_lows"))

    # ------------------------------------------------------------------
    # Guard: if current_price is missing we cannot compute any levels
    # ------------------------------------------------------------------
    if current_price is None:
        return TradeLevelsResult(
            current_price=None,
            preferred_entry=None,
            aggressive_entry_min=None,
            aggressive_entry_max=None,
            confirmation_trigger=None,
            add_level=None,
            invalidation_level=None,
            target_1=None,
            target_2=None,
            chase_above=None,
            method="no_setup",
            warnings=["current_price (latest_candle.close) unavailable; cannot calculate trade levels"],
        )

    # ------------------------------------------------------------------
    # Resolve ATR (with proxy fallback)
    # ------------------------------------------------------------------
    atr = _atr_or_proxy(atr_raw, current_price, warnings)
    if atr is None:
        return TradeLevelsResult(
            current_price=_rp(current_price),
            preferred_entry=None,
            aggressive_entry_min=None,
            aggressive_entry_max=None,
            confirmation_trigger=None,
            add_level=None,
            invalidation_level=None,
            target_1=None,
            target_2=None,
            chase_above=None,
            method="no_setup",
            warnings=warnings + ["ATR and current_price both unavailable; cannot calculate trade levels"],
        )

    # ------------------------------------------------------------------
    # Warn on missing support / resistance
    # ------------------------------------------------------------------
    if support_level is None:
        warnings.append("support_level unavailable from price_action_structure")
    if resistance_level is None:
        warnings.append("resistance_level unavailable from price_action_structure")

    # ------------------------------------------------------------------
    # Method selection
    # ------------------------------------------------------------------
    uptrend_conditions = trend in ("uptrend", "strong_uptrend")
    downtrend_conditions = trend in ("downtrend", "strong_downtrend")

    is_breakout = (breakout_label == "confirmed_breakout") or (
        breakout_attempt and uptrend_conditions
    )
    is_pullback = (
        pullback_to_sma20
        or pullback_to_sma50
        or (uptrend_conditions and higher_highs)
    )
    is_breakdown = downtrend_conditions and lower_highs

    # Priority: breakout > pullback > breakdown > no_setup
    if is_breakout:
        levels = _build_breakout(
            current_price=current_price,
            atr=atr,
            resistance_level=resistance_level,
            support_level=support_level,
            sma_20=sma_20_val,
            warnings=warnings,
        )
        method = "breakout"

    elif is_pullback:
        levels = _build_pullback(
            current_price=current_price,
            atr=atr,
            resistance_level=resistance_level,
            support_level=support_level,
            sma_20=sma_20_val,
            sma_50=sma_50_val,
            high_20d=high_20d,
            pullback_to_sma20=pullback_to_sma20,
            pullback_to_sma50=pullback_to_sma50,
            warnings=warnings,
        )
        method = "pullback"

    elif is_breakdown:
        levels = _build_breakdown(
            current_price=current_price,
            atr=atr,
            resistance_level=resistance_level,
            support_level=support_level,
            warnings=warnings,
        )
        method = "breakdown"

    else:
        return TradeLevelsResult(
            current_price=_rp(current_price),
            preferred_entry=None,
            aggressive_entry_min=None,
            aggressive_entry_max=None,
            confirmation_trigger=None,
            add_level=None,
            invalidation_level=None,
            target_1=None,
            target_2=None,
            chase_above=None,
            method="no_setup",
            warnings=warnings + ["Insufficient price structure to calculate reliable trade levels"],
        )

    return TradeLevelsResult(
        current_price=_rp(current_price),
        method=method,
        warnings=warnings,
        **levels,
    )
