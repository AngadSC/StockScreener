"""Tests for the Daily Market Brief.

Covers the market payload builder (with the liquidity filter), the email
render + subject, and the LLM generate path (validation, retry, Redis caching,
and the EMAIL_ENABLED gate). No network and no live Postgres — an in-memory
SQLite DB is used (same pattern as test_email_service.py) with the LLM and
Redis cache mocked.
"""

from __future__ import annotations

import os

# App config requires these; set safe dummies before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402


# StockFundamental.additional_data is a Postgres JSONB column; teach SQLite to
# render it as JSON so the table can be created in-memory for these tests.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "JSON"


from app.ai import market_brief  # noqa: E402
from app.database.models import DailyOHLCV, StockFundamental, Ticker  # noqa: E402


# Latest trading day = Monday; prior = the preceding Friday.
LATEST = date(2026, 7, 20)
PRIOR = date(2026, 7, 17)


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Ticker.__table__.create(engine)
    DailyOHLCV.__table__.create(engine)
    StockFundamental.__table__.create(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_ticker(db: Session, tid: int, symbol: str, name: str, sector=None, avg_volume=None):
    db.add(Ticker(id=tid, symbol=symbol, name=name))
    if sector is not None or avg_volume is not None:
        db.add(StockFundamental(ticker_id=tid, sector=sector, avg_volume=avg_volume))


def _add_prices(db: Session, tid: int, close_latest: float, close_prior: float, volume: int = 5_000_000):
    db.add(DailyOHLCV(ticker_id=tid, date=PRIOR, open=close_prior, high=close_prior,
                      low=close_prior, close=close_prior, volume=volume))
    db.add(DailyOHLCV(ticker_id=tid, date=LATEST, open=close_latest, high=close_latest,
                      low=close_latest, close=close_latest, volume=volume))


@pytest.fixture
def seeded(db: Session) -> Session:
    # Index proxies.
    _add_ticker(db, 1, "SPY", "SPDR S&P 500 ETF", sector="ETF", avg_volume=70_000_000)
    _add_prices(db, 1, 545.0, 540.0)
    _add_ticker(db, 2, "QQQ", "Invesco QQQ", sector="ETF", avg_volume=40_000_000)
    _add_prices(db, 2, 470.0, 465.0)

    # Sector constituents (liquid).
    _add_ticker(db, 3, "AAPL", "Apple Inc.", sector="Technology", avg_volume=50_000_000)
    _add_prices(db, 3, 190.0, 185.0)  # +2.70% (top gainer)
    _add_ticker(db, 4, "MSFT", "Microsoft Corp.", sector="Technology", avg_volume=25_000_000)
    _add_prices(db, 4, 410.0, 415.0)  # -1.20%
    _add_ticker(db, 5, "XOM", "Exxon Mobil", sector="Energy", avg_volume=15_000_000)
    _add_prices(db, 5, 110.0, 108.0)  # +1.85%
    _add_ticker(db, 6, "JPM", "JPMorgan Chase", sector="Financials", avg_volume=9_000_000)
    _add_prices(db, 6, 200.0, 205.0)  # -2.44% (top loser)

    # Illiquid penny stock — must be excluded from movers/breadth/sectors.
    _add_ticker(db, 7, "PNNY", "Penny Co.", sector="Technology", avg_volume=10_000)
    _add_prices(db, 7, 1.10, 1.00, volume=10_000)

    db.commit()
    return db


# ----------------------------------------------------------------------------
# Payload builder
# ----------------------------------------------------------------------------
def test_build_payload_shape(seeded: Session):
    payload = market_brief.build_brief_payload(seeded)
    assert payload is not None
    assert payload["as_of_date"] == LATEST.isoformat()
    assert payload["prior_date"] == PRIOR.isoformat()

    # Index proxies present, in canonical order, with correct % change.
    symbols = [i["symbol"] for i in payload["indices"]]
    assert symbols == ["SPY", "QQQ"]  # DIA / IWM absent -> skipped
    spy = payload["indices"][0]
    assert spy["close"] == 545.0
    assert spy["change_pct"] == pytest.approx(0.93, abs=0.01)

    # Sectors sorted by avg change, descending.
    changes = [s["avg_change_pct"] for s in payload["sectors"]]
    assert changes == sorted(changes, reverse=True)
    sectors_by_name = {s["sector"]: s for s in payload["sectors"]}
    assert "Technology" in sectors_by_name
    tech = sectors_by_name["Technology"]
    # AAPL up + MSFT down (PNNY excluded as illiquid) -> 1 adv / 1 dec.
    assert tech["advancers"] == 1
    assert tech["decliners"] == 1
    assert tech["count"] == 2


def test_top_movers_and_breadth(seeded: Session):
    payload = market_brief.build_brief_payload(seeded)
    assert payload["top_gainers"][0]["symbol"] == "AAPL"
    assert payload["top_losers"][0]["symbol"] == "JPM"

    # Liquid universe = SPY, QQQ, AAPL, MSFT, XOM, JPM (6). PNNY excluded.
    breadth = payload["breadth"]
    assert breadth["total"] == 6
    assert breadth["advancers"] == 4  # SPY, QQQ, AAPL, XOM
    assert breadth["decliners"] == 2  # MSFT, JPM
    assert breadth["pct_up"] == pytest.approx(66.7, abs=0.1)


def test_illiquid_penny_excluded(seeded: Session):
    payload = market_brief.build_brief_payload(seeded)
    all_symbols = {m["symbol"] for m in payload["top_gainers"] + payload["top_losers"]}
    assert "PNNY" not in all_symbols
    assert payload["universe_size"] == 6


def test_build_payload_insufficient_data(db: Session):
    # Only one date of data -> cannot compute change.
    _add_ticker(db, 1, "SPY", "SPDR S&P 500 ETF", sector="ETF", avg_volume=70_000_000)
    db.add(DailyOHLCV(ticker_id=1, date=LATEST, open=1, high=1, low=1, close=545.0, volume=1_000_000))
    db.commit()
    assert market_brief.build_brief_payload(db) is None


# ----------------------------------------------------------------------------
# Render + subject
# ----------------------------------------------------------------------------
def _sample_brief() -> dict:
    return {
        "headline": "Stocks edge higher as technology leads broad gains",
        "market_summary": "Major indices rose modestly with positive breadth.",
        "sector_rotation": "Technology and Energy led; Financials lagged.",
        "notable_movers": "AAPL led gainers while JPM slipped.",
        "watch_today": ["Watch tech follow-through", "Monitor breadth", "Energy strength"],
    }


def test_render_brief_html(seeded: Session):
    payload = market_brief.build_brief_payload(seeded)
    html = market_brief.render_brief_html(payload, _sample_brief())

    assert isinstance(html, str) and html
    assert "Major Indices" in html
    assert "Sector Rotation" in html
    assert "Notable Movers" in html
    assert "What to Watch Today" in html
    assert "AAPL" in html and "JPM" in html
    assert "SPY" in html
    assert "Open the screener" in html
    assert "/screener" in html
    assert "Watch tech follow-through" in html
    # Bullets rendered as a list.
    assert "<ul" in html and "<li" in html


def test_brief_subject_format():
    payload = {"as_of_date": LATEST.isoformat()}
    subject = market_brief.brief_subject(payload, _sample_brief())
    assert subject.startswith("Market Brief — Mon Jul 20:")
    assert "technology leads" in subject


def test_render_handles_missing_indices():
    payload = {
        "indices": [],
        "sectors": [],
        "top_gainers": [],
        "top_losers": [],
        "breadth": {"pct_up": 0.0, "pct_down": 0.0},
    }
    html = market_brief.render_brief_html(payload, _sample_brief())
    assert "Index data was unavailable" in html


# ----------------------------------------------------------------------------
# LLM generate: validation, retry, caching, and the EMAIL_ENABLED gate
# ----------------------------------------------------------------------------
class _FakeCache:
    """In-memory stand-in for cache_service."""

    def __init__(self):
        self.store: dict = {}
        self.sets: list = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl=None):
        self.store[key] = value
        self.sets.append((key, ttl))
        return True


@pytest.fixture
def fake_cache(monkeypatch):
    cache = _FakeCache()
    monkeypatch.setattr(market_brief, "cache_service", cache)
    return cache


def _valid_raw() -> dict:
    return {
        "headline": "Stocks edge higher",
        "market_summary": "Indices rose with positive breadth.",
        "sector_rotation": "Tech led; Financials lagged.",
        "notable_movers": "AAPL up, JPM down.",
        "watch_today": ["A", "B", "C"],
    }


def test_generate_brief_success_and_cache(monkeypatch, fake_cache):
    monkeypatch.setattr(market_brief.settings, "EMAIL_ENABLED", True)
    calls = {"n": 0}

    def fake_raw(payload, retry):
        calls["n"] += 1
        return _valid_raw(), 1200, 300

    monkeypatch.setattr(market_brief, "_generate_raw_brief", fake_raw)

    payload = {"as_of_date": "2026-07-20", "prior_date": "2026-07-17",
               "indices": [], "sectors": [], "top_gainers": [], "top_losers": [],
               "breadth": {}, "universe_size": 0}

    brief = market_brief.generate_brief(payload)
    assert brief is not None
    assert brief["headline"] == "Stocks edge higher"
    assert brief["watch_today"] == ["A", "B", "C"]
    assert brief["_usage"]["tokens_input"] == 1200
    assert calls["n"] == 1
    # Cached under brief:<date> with the 48h TTL.
    assert ("brief:2026-07-20", market_brief.BRIEF_CACHE_TTL_SECONDS) in fake_cache.sets

    # Second call reads the cache — no second LLM call.
    brief2 = market_brief.generate_brief(payload)
    assert brief2["headline"] == "Stocks edge higher"
    assert calls["n"] == 1


def test_generate_brief_retries_once(monkeypatch, fake_cache):
    monkeypatch.setattr(market_brief.settings, "EMAIL_ENABLED", True)
    calls = {"n": 0}

    def flaky_raw(payload, retry):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"headline": ""}, 10, 5  # invalid -> triggers retry
        return _valid_raw(), 1000, 250

    monkeypatch.setattr(market_brief, "_generate_raw_brief", flaky_raw)

    payload = {"as_of_date": "2026-07-20"}
    brief = market_brief.generate_brief(payload)
    assert brief is not None
    assert calls["n"] == 2  # retried exactly once


def test_generate_brief_gives_up_after_retry(monkeypatch, fake_cache):
    monkeypatch.setattr(market_brief.settings, "EMAIL_ENABLED", True)
    calls = {"n": 0}

    def bad_raw(payload, retry):
        calls["n"] += 1
        return {"nope": True}, 10, 5

    monkeypatch.setattr(market_brief, "_generate_raw_brief", bad_raw)
    brief = market_brief.generate_brief({"as_of_date": "2026-07-20"})
    assert brief is None
    assert calls["n"] == 2
    # Nothing cached on failure.
    assert fake_cache.sets == []


def test_generate_brief_skips_when_email_disabled(monkeypatch, fake_cache):
    monkeypatch.setattr(market_brief.settings, "EMAIL_ENABLED", False)
    called = {"n": 0}

    def raw(payload, retry):
        called["n"] += 1
        return _valid_raw(), 1, 1

    monkeypatch.setattr(market_brief, "_generate_raw_brief", raw)

    assert market_brief.generate_brief({"as_of_date": "2026-07-20"}) is None
    assert called["n"] == 0  # no tokens burned


def test_generate_brief_force_overrides_disabled(monkeypatch, fake_cache):
    monkeypatch.setattr(market_brief.settings, "EMAIL_ENABLED", False)
    monkeypatch.setattr(market_brief, "_generate_raw_brief", lambda p, retry: (_valid_raw(), 1, 1))

    brief = market_brief.generate_brief({"as_of_date": "2026-07-20"}, force=True)
    assert brief is not None
    assert brief["headline"] == "Stocks edge higher"


def test_generate_brief_none_payload():
    assert market_brief.generate_brief(None) is None
