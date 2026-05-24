"""
Unit tests for app.ai.trade_levels.build_trade_levels().

Each test constructs a minimal technical_summary dict that mimics exactly
what _technical_summary() in payload_builder.py produces, then asserts on the
returned TradeLevelsResult fields.

No DB, network, or external fixtures are needed — all inputs are synthetic.
"""
from __future__ import annotations

import pytest

from app.ai.trade_levels import build_trade_levels, _round_price


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ts(
    *,
    close: float | None = 50.0,
    atr: float | None = 1.5,
    sma_20: float | None = 48.0,
    sma_50: float | None = 45.0,
    sma_200: float | None = 40.0,
    trend: str = "uptrend",
    support_level: float | None = 46.0,
    resistance_level: float | None = 54.0,
    high_20d: float | None = 55.0,
    low_20d: float | None = 44.0,
    breakout_label: str = "no_breakout_setup",
    breakout_attempt: bool = False,
    pullback_to_sma20: bool = False,
    pullback_to_sma50: bool = False,
    higher_highs_higher_lows: bool = False,
    lower_highs_lower_lows: bool = False,
) -> dict:
    """
    Build a minimal technical_summary dict in the same shape that
    _technical_summary() in payload_builder.py produces.
    """
    return {
        "latest_candle": {"close": close},
        "atr_14": atr,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "trend": trend,
        "price_levels": {
            "high_20d": high_20d,
            "low_20d": low_20d,
            "high_60d": None,
            "low_60d": None,
        },
        "price_action_structure": {
            "support_level": support_level,
            "resistance_level": resistance_level,
            "breakout_label": breakout_label,
            "breakout_attempt": breakout_attempt,
            "pullback_to_sma20": pullback_to_sma20,
            "pullback_to_sma50": pullback_to_sma50,
            "higher_highs_higher_lows": higher_highs_higher_lows,
            "lower_highs_lower_lows": lower_highs_lower_lows,
            # other keys that build_trade_levels does not use can be absent
        },
    }


EMPTY_SCORES: dict = {}


# ---------------------------------------------------------------------------
# 1. Bullish breakout setup
# ---------------------------------------------------------------------------

class TestBreakoutSetup:
    """confirmed_breakout label with uptrend → breakout method."""

    def setup_method(self):
        self.ts = _make_ts(
            close=54.0,
            atr=1.5,
            sma_20=51.0,
            sma_50=48.0,
            trend="uptrend",
            support_level=49.0,
            resistance_level=53.0,
            breakout_label="confirmed_breakout",
            breakout_attempt=False,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "breakout"

    def test_current_price(self):
        assert self.result["current_price"] == _round_price(54.0)

    def test_confirmation_trigger(self):
        # confirmation_trigger = resistance + 0.15 * atr = 53.0 + 0.225 = 53.225 → 53.23
        expected = _round_price(53.0 + 0.15 * 1.5)
        assert self.result["confirmation_trigger"] == expected

    def test_preferred_entry_equals_confirmation_trigger(self):
        assert self.result["preferred_entry"] == self.result["confirmation_trigger"]

    def test_aggressive_entry_min(self):
        # max(sma_20, support_level) = max(51, 49) = 51
        assert self.result["aggressive_entry_min"] == _round_price(51.0)

    def test_aggressive_entry_max(self):
        # current_price
        assert self.result["aggressive_entry_max"] == _round_price(54.0)

    def test_invalidation_level(self):
        # support_level - 0.20 * atr = 49 - 0.30 = 48.70
        expected = _round_price(49.0 - 0.20 * 1.5)
        assert self.result["invalidation_level"] == expected

    def test_target_1_is_1r(self):
        entry = self.result["preferred_entry"]
        expected = _round_price(entry + 1.0 * 1.5)
        assert self.result["target_1"] == expected

    def test_target_2_is_2r(self):
        entry = self.result["preferred_entry"]
        expected = _round_price(entry + 2.0 * 1.5)
        assert self.result["target_2"] == expected

    def test_add_level_equals_target_1(self):
        assert self.result["add_level"] == self.result["target_1"]

    def test_chase_above(self):
        entry = self.result["preferred_entry"]
        expected = _round_price(entry + 1.25 * 1.5)
        assert self.result["chase_above"] == expected

    def test_no_critical_warnings(self):
        # No warnings should mention missing support or resistance here
        for w in self.result["warnings"]:
            assert "current_price" not in w.lower()
            assert "atr unavailable" not in w.lower()


class TestBreakoutAttemptWithUptrend:
    """breakout_attempt=True + uptrend also triggers breakout method."""

    def setup_method(self):
        self.ts = _make_ts(
            close=52.0,
            atr=2.0,
            sma_20=50.0,
            trend="strong_uptrend",
            support_level=48.0,
            resistance_level=52.5,
            breakout_label="breakout_attempt",
            breakout_attempt=True,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "breakout"

    def test_confirmation_trigger_above_resistance(self):
        assert self.result["confirmation_trigger"] > 52.5


# ---------------------------------------------------------------------------
# 2. Bullish pullback setup
# ---------------------------------------------------------------------------

class TestPullbackToSma20:
    """pullback_to_sma20=True → pullback method."""

    def setup_method(self):
        self.ts = _make_ts(
            close=49.5,
            atr=1.2,
            sma_20=49.0,
            sma_50=46.0,
            trend="uptrend",
            support_level=47.0,
            resistance_level=55.0,
            high_20d=55.0,
            breakout_label="pullback_to_sma20",
            pullback_to_sma20=True,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "pullback"

    def test_preferred_entry_is_sma20(self):
        assert self.result["preferred_entry"] == _round_price(49.0)

    def test_aggressive_entry_min_below_entry(self):
        # min(sma_20, support) = min(49, 47) = 47
        assert self.result["aggressive_entry_min"] == _round_price(47.0)

    def test_aggressive_entry_max(self):
        # max(sma_20, current * 0.99) = max(49, 49.005) = 49.005 → 49.01 (or similar)
        expected = _round_price(max(49.0, 49.5 * 0.99))
        assert self.result["aggressive_entry_max"] == expected

    def test_confirmation_trigger_uses_resistance(self):
        # resistance_level available → use it
        assert self.result["confirmation_trigger"] == _round_price(55.0)

    def test_target_1_is_1r_from_preferred_entry(self):
        entry = self.result["preferred_entry"]
        assert self.result["target_1"] == _round_price(entry + 1.2)

    def test_target_2_is_resistance_when_greater(self):
        # resistance (55) > target_1 (~50.2) → target_2 = resistance
        assert self.result["target_2"] == _round_price(55.0)

    def test_chase_above_is_1_5r_from_entry(self):
        entry = self.result["preferred_entry"]
        assert self.result["chase_above"] == _round_price(entry + 1.5 * 1.2)


class TestPullbackHigherHighsLowerLows:
    """uptrend + higher_highs_higher_lows=True → pullback method (no explicit pullback flag needed)."""

    def setup_method(self):
        self.ts = _make_ts(
            trend="strong_uptrend",
            higher_highs_higher_lows=True,
            pullback_to_sma20=False,
            pullback_to_sma50=False,
            breakout_label="no_breakout_setup",
            breakout_attempt=False,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "pullback"


# ---------------------------------------------------------------------------
# 3. Bearish breakdown
# ---------------------------------------------------------------------------

class TestBreakdown:
    """downtrend + lower_highs_lower_lows=True → breakdown method."""

    def setup_method(self):
        self.ts = _make_ts(
            close=38.0,
            atr=1.8,
            sma_20=40.0,
            sma_50=43.0,
            trend="downtrend",
            support_level=36.0,
            resistance_level=42.0,
            breakout_label="no_breakout_setup",
            lower_highs_lower_lows=True,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "breakdown"

    def test_confirmation_trigger_below_support(self):
        # support - 0.15 * atr = 36 - 0.27 = 35.73
        expected = _round_price(36.0 - 0.15 * 1.8)
        assert self.result["confirmation_trigger"] == expected

    def test_preferred_entry_equals_confirmation_trigger(self):
        assert self.result["preferred_entry"] == self.result["confirmation_trigger"]

    def test_aggressive_entry_min_is_current_price(self):
        assert self.result["aggressive_entry_min"] == _round_price(38.0)

    def test_aggressive_entry_max_is_resistance(self):
        assert self.result["aggressive_entry_max"] == _round_price(42.0)

    def test_invalidation_above_resistance(self):
        # resistance + 0.20 * atr = 42 + 0.36 = 42.36
        expected = _round_price(42.0 + 0.20 * 1.8)
        assert self.result["invalidation_level"] == expected

    def test_target_1_downside(self):
        entry = self.result["preferred_entry"]
        expected = _round_price(entry - 1.0 * 1.8)
        assert self.result["target_1"] == expected

    def test_target_2_downside(self):
        entry = self.result["preferred_entry"]
        expected = _round_price(entry - 2.0 * 1.8)
        assert self.result["target_2"] == expected

    def test_chase_above_is_none(self):
        assert self.result["chase_above"] is None

    def test_add_level_equals_target_1(self):
        assert self.result["add_level"] == self.result["target_1"]


# ---------------------------------------------------------------------------
# 4. Missing ATR → proxy used
# ---------------------------------------------------------------------------

class TestMissingAtr:
    """ATR=None → fall back to 3% of current price; warning added."""

    def setup_method(self):
        self.ts = _make_ts(
            close=100.0,
            atr=None,
            sma_20=98.0,
            trend="uptrend",
            support_level=95.0,
            resistance_level=105.0,
            breakout_label="confirmed_breakout",
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_still_resolved(self):
        # even with no ATR, breakout label drives method
        assert self.result["method"] == "breakout"

    def test_proxy_warning_present(self):
        assert any("3% price proxy" in w for w in self.result["warnings"])

    def test_proxy_atr_is_3_pct(self):
        proxy_atr = 100.0 * 0.03  # 3.0
        entry = self.result["preferred_entry"]
        assert entry is not None
        # confirmation_trigger = resistance + 0.15 * proxy = 105 + 0.45 = 105.45
        expected_ct = _round_price(105.0 + 0.15 * proxy_atr)
        assert self.result["confirmation_trigger"] == expected_ct

    def test_targets_use_proxy(self):
        proxy_atr = 3.0
        entry = self.result["preferred_entry"]
        assert self.result["target_1"] == _round_price(entry + 1.0 * proxy_atr)
        assert self.result["target_2"] == _round_price(entry + 2.0 * proxy_atr)


# ---------------------------------------------------------------------------
# 5. Missing support and resistance
# ---------------------------------------------------------------------------

class TestMissingSupportAndResistance:
    """Both support_level and resistance_level are None → degraded output + warnings."""

    def setup_method(self):
        self.ts = _make_ts(
            close=75.0,
            atr=2.0,
            sma_20=73.0,
            sma_50=70.0,
            trend="uptrend",
            support_level=None,
            resistance_level=None,
            high_20d=78.0,
            breakout_label="confirmed_breakout",
            breakout_attempt=False,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_still_breakout(self):
        # confirmed_breakout label takes effect regardless of missing levels
        assert self.result["method"] == "breakout"

    def test_support_warning(self):
        assert any("support_level" in w for w in self.result["warnings"])

    def test_resistance_warning(self):
        assert any("resistance_level" in w for w in self.result["warnings"])

    def test_aggressive_entry_min_none_when_no_support_or_sma(self):
        # sma_20 IS available here (73.0), so aggressive_entry_min should be sma_20
        assert self.result["aggressive_entry_min"] == _round_price(73.0)

    def test_confirmation_trigger_falls_back_to_price_based(self):
        # resistance_level=None → fallback: current_price + 0.15 * atr
        expected = _round_price(75.0 + 0.15 * 2.0)
        assert self.result["confirmation_trigger"] == expected

    def test_invalidation_falls_back(self):
        # support=None → current_price - 1.5 * atr = 75 - 3.0 = 72
        expected = _round_price(75.0 - 1.5 * 2.0)
        assert self.result["invalidation_level"] == expected

    def test_current_price_present(self):
        assert self.result["current_price"] == _round_price(75.0)


class TestOnlySupportMissing:
    """support_level=None but resistance available for breakout."""

    def setup_method(self):
        self.ts = _make_ts(
            close=50.0,
            atr=1.0,
            sma_20=49.0,
            trend="uptrend",
            support_level=None,
            resistance_level=52.0,
            breakout_label="confirmed_breakout",
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_invalidation_uses_price_minus_atr_fallback(self):
        # support unavailable → current_price - 1.5 * atr = 50 - 1.5 = 48.5
        expected = _round_price(50.0 - 1.5 * 1.0)
        assert self.result["invalidation_level"] == expected

    def test_aggressive_entry_min_uses_sma20(self):
        # sma_20 available, support not → aggressive_entry_min = sma_20
        assert self.result["aggressive_entry_min"] == _round_price(49.0)


# ---------------------------------------------------------------------------
# 6. No setup (sideways + no flags)
# ---------------------------------------------------------------------------

class TestNoSetup:
    """Sideways trend, no breakout / pullback / breakdown flags → no_setup."""

    def setup_method(self):
        self.ts = _make_ts(
            trend="sideways",
            breakout_label="no_breakout_setup",
            breakout_attempt=False,
            pullback_to_sma20=False,
            pullback_to_sma50=False,
            higher_highs_higher_lows=False,
            lower_highs_lower_lows=False,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_is_no_setup(self):
        assert self.result["method"] == "no_setup"

    def test_all_price_levels_none(self):
        price_keys = [
            "preferred_entry",
            "aggressive_entry_min",
            "aggressive_entry_max",
            "confirmation_trigger",
            "add_level",
            "invalidation_level",
            "target_1",
            "target_2",
            "chase_above",
        ]
        for key in price_keys:
            assert self.result[key] is None, f"Expected {key} to be None, got {self.result[key]}"

    def test_warning_present(self):
        assert any("Insufficient price structure" in w for w in self.result["warnings"])

    def test_current_price_still_present(self):
        # current_price is always filled if close is available
        assert self.result["current_price"] is not None


class TestNoSetupDowntrendWithoutLowerStructure:
    """Downtrend but lower_highs_lower_lows=False → no_setup (breakdown requires both flags)."""

    def setup_method(self):
        self.ts = _make_ts(
            trend="downtrend",
            lower_highs_lower_lows=False,
            breakout_label="no_breakout_setup",
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_is_no_setup(self):
        assert self.result["method"] == "no_setup"


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------

class TestMissingCurrentPrice:
    """No close price → immediate no_setup with explanatory warning."""

    def setup_method(self):
        self.ts = _make_ts(close=None)
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_is_no_setup(self):
        assert self.result["method"] == "no_setup"

    def test_current_price_is_none(self):
        assert self.result["current_price"] is None

    def test_warning_mentions_current_price(self):
        assert any("current_price" in w.lower() for w in self.result["warnings"])


class TestSubFiveDollarStock:
    """Price < $5 → 3-decimal rounding applied."""

    def setup_method(self):
        self.ts = _make_ts(
            close=3.50,
            atr=0.12,
            sma_20=3.40,
            sma_50=3.20,
            trend="uptrend",
            support_level=3.30,
            resistance_level=3.70,
            breakout_label="confirmed_breakout",
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method(self):
        assert self.result["method"] == "breakout"

    def test_prices_have_3_decimal_precision(self):
        # All computed levels should be rounded to 3 decimal places for sub-$5
        ct = self.result["confirmation_trigger"]
        assert ct is not None
        # Check that the value equals its 3-decimal rounded version
        assert ct == round(ct, 3)

    def test_current_price_rounded(self):
        assert self.result["current_price"] == round(3.50, 3)


class TestRoundPriceHelper:
    """Direct tests for the _round_price helper."""

    def test_above_five_rounds_to_2dp(self):
        assert _round_price(12.3456) == 12.35

    def test_below_five_rounds_to_3dp(self):
        assert _round_price(1.23456) == 1.235

    def test_exactly_five_rounds_to_2dp(self):
        # boundary: price < 5 → 3dp, but 5.0 is not < 5
        assert _round_price(5.0) == 5.0
        assert _round_price(4.9999) == round(4.9999, 3)


class TestPullbackFallsBackToHighWhenNoResistance:
    """Pullback method: if resistance=None, confirmation_trigger uses high_20d."""

    def setup_method(self):
        self.ts = _make_ts(
            close=49.0,
            atr=1.0,
            sma_20=48.5,
            sma_50=46.0,
            trend="uptrend",
            support_level=45.0,
            resistance_level=None,
            high_20d=52.0,
            pullback_to_sma20=True,
        )
        self.result = build_trade_levels(self.ts, EMPTY_SCORES)

    def test_method_is_pullback(self):
        assert self.result["method"] == "pullback"

    def test_confirmation_trigger_uses_high_20d(self):
        assert self.result["confirmation_trigger"] == _round_price(52.0)

    def test_target_2_falls_back_to_2r(self):
        # resistance=None so target_2 = preferred_entry + 2 * atr
        entry = self.result["preferred_entry"]
        assert self.result["target_2"] == _round_price(entry + 2.0 * 1.0)
