"""
Unit tests for the earnings calendar + FRED macro dashboard feature.

No DB, network, or external fixtures — the earnings scope query test uses a
MagicMock db session that mimics the SQLAlchemy fluent chain (matching the
project's existing test style, e.g. tests/test_backtest_portfolio.py).
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

from app.services.earnings import (
    MARKET_TZ,
    _merge_scope_symbols,
    chunk_symbols,
    get_earnings_scope_tickers,
    parse_calendar_event,
)
from app.services.fred import compute_yoy_series, parse_fred_value


# ---------------------------------------------------------------------------
# FRED: '.' missing-value handling
# ---------------------------------------------------------------------------

def test_parse_fred_value_handles_missing_sentinel():
    assert parse_fred_value(".") is None


def test_parse_fred_value_handles_none_and_blank():
    assert parse_fred_value(None) is None
    assert parse_fred_value("") is None
    assert parse_fred_value("   ") is None


def test_parse_fred_value_parses_numeric_strings():
    assert parse_fred_value("4.33") == 4.33
    assert parse_fred_value("-0.12") == -0.12


def test_parse_fred_value_passes_through_numbers():
    assert parse_fred_value(4.5) == 4.5
    assert parse_fred_value(10) == 10.0


def test_parse_fred_value_rejects_garbage():
    assert parse_fred_value("not-a-number") is None


# ---------------------------------------------------------------------------
# FRED: CPI YoY transform
# ---------------------------------------------------------------------------

def test_compute_yoy_series_basic_percent_change():
    observations = [
        (date(2024, 1, 1), 300.0),
        (date(2025, 1, 1), 315.0),  # +5% YoY vs Jan 2024
    ]
    result = compute_yoy_series(observations)
    assert result == [(date(2025, 1, 1), 5.0)]


def test_compute_yoy_series_skips_points_without_prior_year_match():
    observations = [
        (date(2024, 3, 1), 300.0),
        (date(2024, 4, 1), 301.0),  # no March/April 2023 comparison available
    ]
    result = compute_yoy_series(observations)
    assert result == []


def test_compute_yoy_series_skips_missing_values():
    observations = [
        (date(2024, 1, 1), None),
        (date(2025, 1, 1), 315.0),
    ]
    result = compute_yoy_series(observations)
    assert result == []


def test_compute_yoy_series_multiple_months():
    observations = [
        (date(2024, 1, 1), 300.0),
        (date(2024, 2, 1), 302.0),
        (date(2025, 1, 1), 309.0),   # +3% YoY
        (date(2025, 2, 1), 308.04),  # +2% YoY
    ]
    result = compute_yoy_series(observations)
    result_dict = dict(result)
    assert round(result_dict[date(2025, 1, 1)], 4) == 3.0
    assert round(result_dict[date(2025, 2, 1)], 4) == 2.0


def test_compute_yoy_series_guards_against_zero_division():
    observations = [
        (date(2024, 1, 1), 0.0),
        (date(2025, 1, 1), 10.0),
    ]
    result = compute_yoy_series(observations)
    assert result == []


# ---------------------------------------------------------------------------
# Earnings: pure merge helper
# ---------------------------------------------------------------------------

def test_merge_scope_symbols_dedupes_and_sorts():
    watchlisted = ["TSLA", "AAPL"]
    top_market_cap = ["AAPL", "MSFT"]
    assert _merge_scope_symbols(watchlisted, top_market_cap) == ["AAPL", "MSFT", "TSLA"]


def test_merge_scope_symbols_handles_empty_lists():
    assert _merge_scope_symbols([], []) == []
    assert _merge_scope_symbols(["AAPL"], []) == ["AAPL"]
    assert _merge_scope_symbols([], ["AAPL"]) == ["AAPL"]


def test_merge_scope_symbols_ignores_falsy_entries():
    assert _merge_scope_symbols(["AAPL", "", None], ["MSFT"]) == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# Earnings: scope query construction (mocked db session)
# ---------------------------------------------------------------------------

def test_get_earnings_scope_tickers_merges_watchlist_and_top_market_cap():
    db = MagicMock()

    # Both branches call db.query(Ticker.symbol).join(...); MagicMock returns the
    # same `.join.return_value` object for any call args, so we configure the
    # two distinct downstream chains (`.distinct()` vs `.filter()`) on it.
    join_mock = db.query.return_value.join.return_value
    join_mock.distinct.return_value.all.return_value = [("AAPL",), ("TSLA",)]
    join_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        ("MSFT",), ("AAPL",),
    ]

    result = get_earnings_scope_tickers(db, top_n=500)

    assert result == ["AAPL", "MSFT", "TSLA"]
    # top_n should flow into .limit(...)
    join_mock.filter.return_value.order_by.return_value.limit.assert_called_with(500)


def test_get_earnings_scope_tickers_empty_when_no_data():
    db = MagicMock()
    join_mock = db.query.return_value.join.return_value
    join_mock.distinct.return_value.all.return_value = []
    join_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    assert get_earnings_scope_tickers(db) == []


# ---------------------------------------------------------------------------
# Earnings: calendar event parsing
# ---------------------------------------------------------------------------

def test_parse_calendar_event_returns_none_for_empty_input():
    assert parse_calendar_event(None) is None
    assert parse_calendar_event({}) is None
    assert parse_calendar_event("error string") is None


def test_parse_calendar_event_returns_none_when_no_earnings_date():
    assert parse_calendar_event({"earnings": {}}) is None
    assert parse_calendar_event({"earnings": {"earningsDate": []}}) is None


def test_parse_calendar_event_parses_single_date():
    raw = {
        "earnings": {
            "earningsDate": [date(2026, 8, 15)],
            "earningsAverage": 1.23,
        }
    }
    parsed = parse_calendar_event(raw)
    assert parsed == {
        "earnings_date": date(2026, 8, 15),
        "time_hint": "unknown",
        "eps_estimate": 1.23,
    }


def test_parse_calendar_event_picks_earliest_of_date_range():
    raw = {
        "earnings": {
            "earningsDate": [
                datetime(2026, 8, 20, 12, 0, tzinfo=MARKET_TZ),
                datetime(2026, 8, 17, 12, 0, tzinfo=MARKET_TZ),
            ],
            "earningsAverage": None,
        }
    }
    parsed = parse_calendar_event(raw)
    assert parsed["earnings_date"] == date(2026, 8, 17)
    assert parsed["eps_estimate"] is None


def test_parse_calendar_event_infers_bmo_and_amc_from_hour():
    """Boundaries are the ET session: before 09:30 is BMO, 16:00 onward is AMC."""
    def at(hour, minute=0):
        return {"earnings": {"earningsDate": [datetime(2026, 8, 15, hour, minute, tzinfo=MARKET_TZ)]}}

    assert parse_calendar_event(at(7))["time_hint"] == "bmo"
    assert parse_calendar_event(at(8, 30))["time_hint"] == "bmo"      # Yahoo's BMO placeholder
    assert parse_calendar_event(at(16))["time_hint"] == "amc"          # Yahoo's AMC placeholder
    assert parse_calendar_event(at(16, 30))["time_hint"] == "amc"
    assert parse_calendar_event(at(13))["time_hint"] == "unknown"      # intraday, don't guess


def test_parse_calendar_event_handles_iso_string_dates():
    raw = {"earnings": {"earningsDate": ["2026-09-01"], "earningsAverage": 0.5}}
    parsed = parse_calendar_event(raw)
    assert parsed["earnings_date"] == date(2026, 9, 1)
    assert parsed["time_hint"] == "unknown"
    assert parsed["eps_estimate"] == 0.5


def test_parse_calendar_event_handles_yahooquery_broken_seconds_format():
    """
    Regression: yahooquery 2.4.x renders earningsDate with a literal "S" instead
    of "%S" ("2026-10-29 14:00:S"). fromisoformat() rejects it, which silently
    emptied the entire earnings calendar.
    """
    raw = {"earnings": {"earningsDate": ["2026-10-29 14:00:S"], "earningsAverage": 1.98}}
    parsed = parse_calendar_event(raw)
    assert parsed is not None
    assert parsed["earnings_date"] == date(2026, 10, 29)
    assert parsed["eps_estimate"] == 1.98


def test_parse_calendar_event_normalises_host_timezone_to_eastern():
    """
    yahooquery builds these strings with a naive datetime.fromtimestamp(), so the
    hour is host-local. A UTC host must still classify a 12:30 UTC (08:30 ET)
    report as BMO rather than 'unknown'.
    """
    raw = {"earnings": {"earningsDate": ["2026-10-29T12:30:00+00:00"]}}
    parsed = parse_calendar_event(raw)
    assert parsed["earnings_date"] == date(2026, 10, 29)
    assert parsed["time_hint"] == "bmo"

    raw_amc = {"earnings": {"earningsDate": ["2026-10-29T20:00:00+00:00"]}}
    assert parse_calendar_event(raw_amc)["time_hint"] == "amc"


def test_parse_calendar_event_handles_epoch_seconds():
    raw = {"earnings": {"earningsDate": [1787774400]}}  # 2026-08-26 16:00 ET
    parsed = parse_calendar_event(raw)
    assert parsed["earnings_date"] == date(2026, 8, 26)
    assert parsed["time_hint"] == "amc"


def test_parse_calendar_event_returns_none_for_unparseable_date():
    assert parse_calendar_event({"earnings": {"earningsDate": ["not-a-date"]}}) is None


# ---------------------------------------------------------------------------
# Earnings: batching
# ---------------------------------------------------------------------------

def test_chunk_symbols_respects_batch_size():
    symbols = [f"SYM{i}" for i in range(120)]
    batches = chunk_symbols(symbols, batch_size=50)
    assert len(batches) == 3
    assert len(batches[0]) == 50
    assert len(batches[1]) == 50
    assert len(batches[2]) == 20


def test_chunk_symbols_empty_list():
    assert chunk_symbols([], batch_size=50) == []
