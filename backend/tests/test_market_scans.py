"""
Unit tests for the pure calculation helpers in app.services.market_scans.

These cover the math and threshold logic (percent change, gap %, junk filters,
52-week proximity, unusual volume, sector aggregation, row/top-N shaping) in
isolation -- no DB, no network, no fixtures. compute_scans() itself (the raw-SQL
orchestration) is intentionally NOT exercised here since it needs a live Postgres
connection; these tests instead pin down every building block it relies on.
"""
from __future__ import annotations

import pytest

from app.services.market_scans import (
    GAP_PCT_THRESHOLD,
    MIN_AVG_VOLUME,
    MIN_CLOSE_PRICE,
    NEAR_52W_PCT_THRESHOLD,
    UNUSUAL_VOLUME_RATIO,
    _empty_payload,
    _finalize_sectors,
    _make_row,
    _new_sector_acc,
    _pct_change,
    _round,
    _top_n,
    effective_avg_volume,
    is_gap_down,
    is_gap_up,
    is_near_52w_high,
    is_near_52w_low,
    is_unusual_volume,
    market_scans_cache_key,
    passes_junk_filter,
    volume_ratio,
)


# ---------------------------------------------------------------------------
# _pct_change
# ---------------------------------------------------------------------------

class TestPctChange:
    def test_simple_gain(self):
        assert _pct_change(110.0, 100.0) == pytest.approx(10.0)

    def test_simple_loss(self):
        assert _pct_change(90.0, 100.0) == pytest.approx(-10.0)

    def test_zero_change(self):
        assert _pct_change(50.0, 50.0) == 0.0

    def test_none_new_value(self):
        assert _pct_change(None, 100.0) is None

    def test_none_base_value(self):
        assert _pct_change(100.0, None) is None

    def test_zero_base_value_avoids_division_by_zero(self):
        assert _pct_change(100.0, 0.0) is None

    def test_gap_percent_use_case(self):
        # open 102, prior close 100 -> +2% gap
        assert _pct_change(102.0, 100.0) == pytest.approx(2.0)
        # open 97, prior close 100 -> -3% gap
        assert _pct_change(97.0, 100.0) == pytest.approx(-3.0)


# ---------------------------------------------------------------------------
# effective_avg_volume
# ---------------------------------------------------------------------------

class TestEffectiveAvgVolume:
    def test_prefers_fundamentals_value(self):
        assert effective_avg_volume(500_000, 100_000) == 500_000

    def test_falls_back_to_computed_when_fundamentals_null(self):
        assert effective_avg_volume(None, 300_000) == 300_000

    def test_falls_back_when_fundamentals_zero(self):
        # 0 is falsy -- treated the same as missing.
        assert effective_avg_volume(0, 300_000) == 300_000

    def test_both_missing(self):
        assert effective_avg_volume(None, None) is None


# ---------------------------------------------------------------------------
# passes_junk_filter
# ---------------------------------------------------------------------------

class TestPassesJunkFilter:
    def test_passes_when_above_both_thresholds(self):
        assert passes_junk_filter(MIN_CLOSE_PRICE + 1, MIN_AVG_VOLUME + 1) is True

    def test_fails_below_min_close_price(self):
        assert passes_junk_filter(1.99, 1_000_000) is False

    def test_fails_exactly_at_min_close_price_boundary(self):
        # MIN_CLOSE_PRICE itself should pass ("last close >= $2")
        assert passes_junk_filter(MIN_CLOSE_PRICE, 1_000_000) is True

    def test_fails_below_min_avg_volume(self):
        assert passes_junk_filter(10.0, MIN_AVG_VOLUME - 1) is False

    def test_fails_when_close_is_none(self):
        assert passes_junk_filter(None, 1_000_000) is False

    def test_fails_when_avg_volume_is_none(self):
        assert passes_junk_filter(10.0, None) is False

    def test_fails_when_avg_volume_is_zero(self):
        assert passes_junk_filter(10.0, 0) is False


# ---------------------------------------------------------------------------
# is_near_52w_high / is_near_52w_low
# ---------------------------------------------------------------------------

class TestNear52wHigh:
    def test_at_the_high_is_near(self):
        assert is_near_52w_high(100.0, 100.0) is True

    def test_within_threshold_is_near(self):
        # 0.5% off the high, threshold is 1%
        assert is_near_52w_high(99.5, 100.0) is True

    def test_exactly_at_threshold_boundary_is_near(self):
        boundary_close = 100.0 * (1 - NEAR_52W_PCT_THRESHOLD / 100.0)
        assert is_near_52w_high(boundary_close, 100.0) is True

    def test_beyond_threshold_is_not_near(self):
        assert is_near_52w_high(95.0, 100.0) is False

    def test_missing_high_is_not_near(self):
        assert is_near_52w_high(100.0, None) is False


class TestNear52wLow:
    def test_at_the_low_is_near(self):
        assert is_near_52w_low(50.0, 50.0) is True

    def test_within_threshold_is_near(self):
        assert is_near_52w_low(50.3, 50.0) is True

    def test_beyond_threshold_is_not_near(self):
        assert is_near_52w_low(55.0, 50.0) is False

    def test_missing_low_is_not_near(self):
        assert is_near_52w_low(50.0, None) is False


# ---------------------------------------------------------------------------
# volume_ratio / is_unusual_volume
# ---------------------------------------------------------------------------

class TestVolumeRatio:
    def test_simple_ratio(self):
        assert volume_ratio(1_000_000, 500_000) == pytest.approx(2.0)

    def test_none_last_volume(self):
        assert volume_ratio(None, 500_000) is None

    def test_none_avg_volume(self):
        assert volume_ratio(1_000_000, None) is None

    def test_zero_avg_volume(self):
        assert volume_ratio(1_000_000, 0) is None


class TestIsUnusualVolume:
    def test_above_threshold(self):
        avg = 100_000
        assert is_unusual_volume(avg * UNUSUAL_VOLUME_RATIO, avg) is True

    def test_below_threshold(self):
        avg = 100_000
        assert is_unusual_volume(avg * (UNUSUAL_VOLUME_RATIO - 0.1), avg) is False

    def test_missing_data(self):
        assert is_unusual_volume(None, None) is False


# ---------------------------------------------------------------------------
# is_gap_up / is_gap_down
# ---------------------------------------------------------------------------

class TestGapThresholds:
    def test_gap_up_at_threshold(self):
        assert is_gap_up(GAP_PCT_THRESHOLD) is True

    def test_gap_up_below_threshold(self):
        assert is_gap_up(GAP_PCT_THRESHOLD - 0.1) is False

    def test_gap_down_at_threshold(self):
        assert is_gap_down(-GAP_PCT_THRESHOLD) is True

    def test_gap_down_above_threshold(self):
        assert is_gap_down(-GAP_PCT_THRESHOLD + 0.1) is False

    def test_small_gap_is_neither(self):
        assert is_gap_up(0.5) is False
        assert is_gap_down(0.5) is False

    def test_none_gap_is_neither(self):
        assert is_gap_up(None) is False
        assert is_gap_down(None) is False

    def test_gap_pct_from_open_and_prior_close(self):
        # open $102 vs prior close $100 -> +2% gap, right at the threshold.
        gap_pct = _pct_change(102.0, 100.0)
        assert is_gap_up(gap_pct) is True
        assert is_gap_down(gap_pct) is False

        # open $97.50 vs prior close $100 -> -2.5% gap, past the threshold.
        gap_pct_down = _pct_change(97.5, 100.0)
        assert is_gap_down(gap_pct_down) is True


# ---------------------------------------------------------------------------
# _round
# ---------------------------------------------------------------------------

class TestRound:
    def test_rounds_to_two_decimals_by_default(self):
        assert _round(1.23456) == 1.23

    def test_none_stays_none(self):
        assert _round(None) is None

    def test_custom_ndigits(self):
        assert _round(1.23456, 3) == 1.235


# ---------------------------------------------------------------------------
# _make_row
# ---------------------------------------------------------------------------

class TestMakeRow:
    def _metrics_row(self, **overrides):
        base = {
            "symbol": "ACME",
            "name": "Acme Corp",
            "sector": "Industrials",
            "last_close": 12.3456,
            "last_volume": 1_000_000,
            "market_cap": 5_000_000_000,
        }
        base.update(overrides)
        return base

    def test_basic_shape(self):
        row = _make_row(self._metrics_row(), change_pct=5.4321, metric=5.4321)
        assert row == {
            "symbol": "ACME",
            "name": "Acme Corp",
            "sector": "Industrials",
            "close": 12.35,
            "change_pct": 5.43,
            "metric": 5.43,
            "volume": 1_000_000,
            "market_cap": 5_000_000_000,
        }

    def test_falls_back_to_symbol_when_name_missing(self):
        row = _make_row(self._metrics_row(name=None), change_pct=None, metric=None)
        assert row["name"] == "ACME"

    def test_null_volume_and_market_cap_pass_through_as_none(self):
        row = _make_row(self._metrics_row(last_volume=None, market_cap=None), change_pct=1.0, metric=1.0)
        assert row["volume"] is None
        assert row["market_cap"] is None


# ---------------------------------------------------------------------------
# _top_n
# ---------------------------------------------------------------------------

class TestTopN:
    def test_sorts_descending(self):
        rows = [(1.0, {"symbol": "A"}), (5.0, {"symbol": "B"}), (3.0, {"symbol": "C"})]
        result = _top_n(rows, reverse=True)
        assert [r["symbol"] for r in result] == ["B", "C", "A"]

    def test_sorts_ascending(self):
        rows = [(1.0, {"symbol": "A"}), (5.0, {"symbol": "B"}), (3.0, {"symbol": "C"})]
        result = _top_n(rows, reverse=False)
        assert [r["symbol"] for r in result] == ["A", "C", "B"]

    def test_respects_n_limit(self):
        rows = [(float(i), {"symbol": str(i)}) for i in range(50)]
        result = _top_n(rows, reverse=True, n=5)
        assert len(result) == 5
        assert result[0]["symbol"] == "49"

    def test_empty_input(self):
        assert _top_n([], reverse=True) == []


# ---------------------------------------------------------------------------
# sector aggregation
# ---------------------------------------------------------------------------

class TestSectorAggregation:
    def test_finalize_computes_average_and_counts(self):
        acc = _new_sector_acc("Technology")
        for change_pct, market_cap in [(5.0, 100), (-2.0, 200), (3.0, 300)]:
            acc["change_sum"] += change_pct
            acc["stock_count"] += 1
            if change_pct > 0:
                acc["advancers"] += 1
            elif change_pct < 0:
                acc["decliners"] += 1
            acc["total_market_cap"] += market_cap

        sectors = _finalize_sectors({"Technology": acc})
        assert len(sectors) == 1
        tech = sectors[0]
        assert tech["sector"] == "Technology"
        assert tech["avg_change_percent"] == pytest.approx(2.0)  # (5 - 2 + 3) / 3
        assert tech["advancers"] == 2
        assert tech["decliners"] == 1
        assert tech["stock_count"] == 3
        assert tech["total_market_cap"] == 600

    def test_finalize_sorts_by_avg_change_descending(self):
        losers_acc = _new_sector_acc("Energy")
        losers_acc["change_sum"] = -10.0
        losers_acc["stock_count"] = 1

        winners_acc = _new_sector_acc("Tech")
        winners_acc["change_sum"] = 10.0
        winners_acc["stock_count"] = 1

        sectors = _finalize_sectors({"Energy": losers_acc, "Tech": winners_acc})
        assert [s["sector"] for s in sectors] == ["Tech", "Energy"]

    def test_finalize_empty_accumulator_dict(self):
        assert _finalize_sectors({}) == []


# ---------------------------------------------------------------------------
# _empty_payload / market_scans_cache_key
# ---------------------------------------------------------------------------

class TestEmptyPayload:
    def test_shape_has_all_scan_keys_empty(self):
        payload = _empty_payload()
        assert payload["as_of_date"] is None
        assert payload["prior_date"] is None
        for key in ["gainers", "losers", "high_52w", "low_52w", "unusual_volume", "gap_up", "gap_down", "sectors"]:
            assert payload[key] == []

    def test_lists_are_independent_objects(self):
        # Guard against a shared-mutable-default bug: mutating one list must not
        # leak into the others.
        payload = _empty_payload()
        payload["gainers"].append({"symbol": "X"})
        assert payload["losers"] == []


class TestMarketScansCacheKey:
    def test_uses_provided_date(self):
        from datetime import date
        assert market_scans_cache_key(date(2026, 7, 20)) == "market:scans:2026-07-20"

    def test_defaults_to_today_and_has_expected_prefix(self):
        key = market_scans_cache_key()
        assert key.startswith("market:scans:")
        # YYYY-MM-DD suffix
        assert len(key.split(":")[-1]) == 10
