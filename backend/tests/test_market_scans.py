"""
Unit tests for the pure calculation helpers in app.services.market_scans.

These cover the math and threshold logic (percent change, gap %, junk filters,
52-week proximity, unusual volume, sector aggregation, row/top-N shaping) in
isolation -- no DB, no network, no fixtures. compute_scans() itself (the raw-SQL
orchestration) is intentionally NOT exercised here since it needs a live Postgres
connection; these tests instead pin down every building block it relies on.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.market_scans import (
    GAP_PCT_THRESHOLD,
    MARKET_SCANS_CACHE_KEY,
    MARKET_SCANS_CACHE_TTL,
    MIN_AVG_VOLUME,
    MIN_CLOSE_PRICE,
    NEAR_52W_PCT_THRESHOLD,
    UNUSUAL_VOLUME_RATIO,
    VOLUME_BASELINE_DAYS,
    _empty_payload,
    _finalize_sectors,
    _make_row,
    _new_sector_acc,
    _pct_change,
    _round,
    _top_n,
    effective_avg_volume,
    expected_latest_trading_day,
    is_cached_payload_fresh,
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

    def test_baseline_must_exclude_the_current_bar(self):
        """Regression: the 20-day baseline used to include the spike itself.

        With `n` quiet bars at volume V and a spike of k*V, a baseline that
        swallows the spike averages to V*(n-1+k)/n, so the ratio reads
        n*k/(n-1+k) instead of k. Every real spike prints smaller than it is,
        and the ones just over the threshold vanish from the tab entirely.
        """
        n = VOLUME_BASELINE_DAYS
        quiet_volume = 100_000.0
        k = UNUSUAL_VOLUME_RATIO  # a genuine 2.5x day
        spike_volume = quiet_volume * k

        # Correct baseline: the n bars BEFORE today, none of them the spike.
        assert volume_ratio(spike_volume, quiet_volume) == pytest.approx(k)
        assert is_unusual_volume(spike_volume, quiet_volume) is True

        # Old behaviour: spike folded into its own baseline -> understated, and
        # for a threshold-grazing day, dropped from the scan.
        diluted_baseline = (quiet_volume * (n - 1) + spike_volume) / n
        diluted_ratio = volume_ratio(spike_volume, diluted_baseline)
        assert diluted_ratio == pytest.approx(n * k / (n - 1 + k))
        assert diluted_ratio < k
        assert is_unusual_volume(spike_volume, diluted_baseline) is False


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
    def test_key_is_stable_and_not_date_stamped(self):
        # Regression: the key used to embed the ET calendar date, so the 22:30 ET
        # warm job wrote market:scans:<D> while every reader after ET midnight
        # asked for market:scans:<D+1> -- a guaranteed miss. One fixed key now.
        assert market_scans_cache_key() == MARKET_SCANS_CACHE_KEY == "market:scans:latest"
        assert market_scans_cache_key() == market_scans_cache_key()

    def test_ttl_outlives_a_long_weekend(self):
        # Friday 22:30 ET write must still be there Monday morning.
        assert MARKET_SCANS_CACHE_TTL >= 2 * 86400


# ---------------------------------------------------------------------------
# cache freshness (expected_latest_trading_day / is_cached_payload_fresh)
# ---------------------------------------------------------------------------

class TestExpectedLatestTradingDay:
    def test_midweek_expects_the_prior_session(self):
        # Wed 2026-07-22 -> Tue 2026-07-21 (21:00 ET sync means Tue's close is
        # the newest one we can count on during Wednesday).
        assert expected_latest_trading_day(date(2026, 7, 22)) == date(2026, 7, 21)

    def test_monday_skips_back_over_the_weekend(self):
        # Mon 2026-07-20 -> Fri 2026-07-17, not Sunday.
        assert expected_latest_trading_day(date(2026, 7, 20)) == date(2026, 7, 17)

    def test_saturday_expects_friday(self):
        assert expected_latest_trading_day(date(2026, 7, 25)) == date(2026, 7, 24)

    def test_skips_back_over_a_market_holiday(self):
        # Fri 2026-07-03 is the observed Independence Day holiday, so the Monday
        # after (2026-07-06) must look back to Thu 2026-07-02.
        assert expected_latest_trading_day(date(2026, 7, 6)) == date(2026, 7, 2)


class TestIsCachedPayloadFresh:
    def test_payload_from_the_expected_session_is_fresh(self):
        # Wednesday reader, Tuesday's payload (written by Tue 22:30 ET warm job).
        payload = {"as_of_date": "2026-07-21"}
        assert is_cached_payload_fresh(payload, date(2026, 7, 22)) is True

    def test_payload_newer_than_expected_is_fresh(self):
        # Same evening, after the 22:30 warm job has already stored Wednesday.
        payload = {"as_of_date": "2026-07-22"}
        assert is_cached_payload_fresh(payload, date(2026, 7, 22)) is True

    def test_payload_from_a_previous_session_is_stale(self):
        # Regression for the miss-by-construction bug: yesterday's-yesterday
        # payload must trigger a recompute, not be served.
        payload = {"as_of_date": "2026-07-20"}
        assert is_cached_payload_fresh(payload, date(2026, 7, 22)) is False

    def test_weekend_serves_fridays_payload(self):
        payload = {"as_of_date": "2026-07-24"}
        assert is_cached_payload_fresh(payload, date(2026, 7, 25)) is True
        assert is_cached_payload_fresh(payload, date(2026, 7, 26)) is True

    def test_missing_or_empty_payload_is_not_fresh(self):
        assert is_cached_payload_fresh(None, date(2026, 7, 22)) is False
        assert is_cached_payload_fresh({}, date(2026, 7, 22)) is False

    def test_empty_payload_shape_is_never_served_from_cache(self):
        # _empty_payload() has as_of_date=None -- an empty/dev DB must not get
        # stuck serving nothing.
        assert is_cached_payload_fresh(_empty_payload(), date(2026, 7, 22)) is False

    def test_unparseable_as_of_date_is_not_fresh(self):
        assert is_cached_payload_fresh({"as_of_date": "not-a-date"}, date(2026, 7, 22)) is False

    def test_accepts_datetime_ish_string(self):
        # cache_service serializes with json.dumps(default=str); be tolerant if a
        # date ever round-trips as "YYYY-MM-DD 00:00:00".
        payload = {"as_of_date": "2026-07-21 00:00:00"}
        assert is_cached_payload_fresh(payload, date(2026, 7, 22)) is True
