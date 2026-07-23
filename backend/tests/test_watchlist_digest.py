"""Tests for the Elite watchlist AI digest.

Uses an in-memory SQLite DB (same pattern as test_email_service.py). The AI
models use Postgres JSONB columns, so a small SQLite compile hook renders those
as JSON before any table is created. The LLM and payload builder are always
mocked — no network, no real Anthropic calls.

Covers: ranking order + section split, truncation note, day-over-day delta
(bias + score), the cache-hit path making no LLM call, the per-run cost guard
stopping LLM calls, and empty-watchlist producing no send.
"""

from __future__ import annotations

import os

# App config requires these; set safe dummies before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import date, datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402


# Render Postgres JSONB as plain JSON on SQLite so the AI tables can be created
# and dict values round-trip in tests.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "JSON"


from app.ai import watchlist_digest as wd  # noqa: E402
from app.ai import report_cache  # noqa: E402
from app.database.models import (  # noqa: E402
    AIStockReport,
    AIUsageEvent,
    EmailPreference,
    EmailSendLog,
    Ticker,
    User,
    Watchlist,
)
from app.jobs import watchlist_digest_job as job  # noqa: E402
from app.utils.market_calendar import get_previous_trading_day  # noqa: E402


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    for model in (User, Ticker, Watchlist, AIStockReport, AIUsageEvent, EmailPreference, EmailSendLog):
        model.__table__.create(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class _DummyCache:
    """Inert stand-in for the Redis cache so tests never touch Redis."""

    def get(self, *_a, **_k):
        return None

    def set(self, *_a, **_k):
        return True

    def delete(self, *_a, **_k):
        return True


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    monkeypatch.setattr(report_cache, "cache_service", _DummyCache())


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    """Fail loudly if a test hits the real LLM path without opting in."""

    def _boom(*_a, **_k):
        raise AssertionError("generate_single_stock_report should not be called here")

    def _no_payload(*_a, **_k):
        raise AssertionError("build_ai_payload should not be called here")

    monkeypatch.setattr(wd, "generate_single_stock_report", _boom)
    monkeypatch.setattr(wd, "build_ai_payload", _no_payload)


# ----------------------------------------------------------------------------
# Seed helpers
# ----------------------------------------------------------------------------
def _make_user(db: Session, *, tier: str = "elite", is_active: bool = True) -> User:
    u = User(email=f"u{db.query(User).count()}@ex.com", password_hash="x", tier=tier, is_active=is_active)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _add_watchlist(db: Session, user: User, symbols: list[str]) -> None:
    """Add tickers + watchlist rows with strictly increasing added_at.

    Ticker.id is a SmallInteger PK, which SQLite will not auto-increment (only
    INTEGER PK gets rowid), so ids are assigned explicitly here.
    """
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    next_id = (db.query(Ticker).count()) + 1
    for i, symbol in enumerate(symbols):
        ticker = Ticker(id=next_id + i, symbol=symbol, name=f"{symbol} Inc.")
        db.add(ticker)
        db.flush()
        db.add(Watchlist(user_id=user.id, ticker_id=ticker.id, added_at=base + timedelta(minutes=i)))
    db.commit()


def _add_report(
    db: Session,
    user: User,
    symbol: str,
    *,
    report_date: date,
    score: float,
    bias: str = "neutral",
    setup: str = "Pullback entry",
    fresh: bool = True,
) -> AIStockReport:
    created = datetime.now(timezone.utc) if fresh else datetime.now(timezone.utc) - timedelta(days=1)
    report = AIStockReport(
        user_id=user.id,
        ticker=symbol.upper(),
        report_date=report_date,
        created_at=created,
        tier_used="elite",
        report_type="swing_trade_research",
        swing_bias=bias,
        setup_type=setup,
        setup_quality_score=score,
        ai_report={
            "directional_bias": bias,
            "setup_type": setup,
            "setup_quality_score": score,
            "entry_zone": "180.00 - 182.00",
            "invalidation_level": "175.00",
            "target_1": "190.00",
            "main_thesis": "A clear, well-defined setup " * 20,
            "final_verdict": "Actionable long on confirmation.",
        },
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _fake_generate(counter: list[str], score: float = 80.0):
    def _inner(payload, user_id, ticker, db):
        counter.append(ticker.upper())
        return {
            "directional_bias": "bullish",
            "setup_type": "Breakout",
            "setup_quality_score": score,
            "entry_timing_score": 60.0,
            "technical_score": 62.0,
            "fundamental_score": 55.0,
            "sentiment_score": 50.0,
            "valuation_score": 48.0,
            "risk_score": 40.0,
            "entry_zone": "100.00 - 101.50",
            "invalidation_level": "97.00",
            "target_1": "110.00",
            "main_thesis": "Freshly generated thesis. " * 15,
            "final_verdict": "Buy on breakout.",
            "_usage": {"model_used": "claude-sonnet-4-6", "tokens_input": 120, "tokens_output": 60},
        }

    return _inner


# ----------------------------------------------------------------------------
# 1. Ranking order + section classification
# ----------------------------------------------------------------------------
def test_ranking_orders_by_score_and_splits_sections(db):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA", "BBB", "CCC", "DDD"])
    today = date.today()
    _add_report(db, user, "AAA", report_date=today, score=40.0)
    _add_report(db, user, "BBB", report_date=today, score=82.0)
    _add_report(db, user, "CCC", report_date=today, score=71.0)
    _add_report(db, user, "DDD", report_date=today, score=55.0)

    digest = wd.build_user_digest(user, db, max_stocks=10)

    assert digest is not None
    # Sorted by setup_quality_score DESC.
    assert [s["ticker"] for s in digest["stocks"]] == ["BBB", "CCC", "DDD", "AAA"]
    # Strongest = score >= 65 OR top 3. So BBB(82), CCC(71), DDD(55 via top-3).
    assert [s["ticker"] for s in digest["strong"]] == ["BBB", "CCC", "DDD"]
    assert [s["ticker"] for s in digest["rest"]] == ["AAA"]
    # "notable" counts only genuine >= threshold setups (not the top-3 fallback).
    assert digest["notable_count"] == 2
    assert digest["llm_calls"] == 0
    assert digest["cache_hits"] == 4


# ----------------------------------------------------------------------------
# 2. Truncation note
# ----------------------------------------------------------------------------
def test_truncation_note_when_watchlist_exceeds_cap(db):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA", "BBB", "CCC"])
    today = date.today()
    # Only the first two (oldest) get analyzed under the cap.
    _add_report(db, user, "AAA", report_date=today, score=70.0)
    _add_report(db, user, "BBB", report_date=today, score=60.0)

    digest = wd.build_user_digest(user, db, max_stocks=2)

    assert digest["total_watchlist"] == 3
    assert digest["analyzed_attempted"] == 2
    assert digest["truncated"] is True
    assert digest["truncation_note"] == "showing 2 of 3"
    # Oldest-first: AAA and BBB are analyzed, CCC is dropped.
    assert {s["ticker"] for s in digest["stocks"]} == {"AAA", "BBB"}
    assert "showing 2 of 3" in wd.render_digest_html(digest)


# ----------------------------------------------------------------------------
# 3. Day-over-day delta (bias change + score delta + setup change)
# ----------------------------------------------------------------------------
def test_delta_detects_bias_and_score_change(db):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA"])
    today = date.today()
    prev_day = get_previous_trading_day(today)
    _add_report(db, user, "AAA", report_date=prev_day, score=55.0, bias="neutral", setup="Pullback entry", fresh=False)
    _add_report(db, user, "AAA", report_date=today, score=71.0, bias="bullish", setup="Breakout")

    digest = wd.build_user_digest(user, db, max_stocks=10)
    entry = digest["stocks"][0]

    assert entry["ticker"] == "AAA"
    assert entry["changed_since_yesterday"] is True
    line = entry["delta_line"]
    assert "55→71" in line
    assert "(+16)" in line
    assert "Neutral → Bullish" in line
    assert "setup:" in line


def test_delta_absent_when_no_previous_report(db):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA"])
    _add_report(db, user, "AAA", report_date=date.today(), score=60.0)

    digest = wd.build_user_digest(user, db, max_stocks=10)
    entry = digest["stocks"][0]

    assert entry["changed_since_yesterday"] is False
    assert entry["delta_line"] is None


# ----------------------------------------------------------------------------
# 4. Cache-hit path performs no LLM call
# ----------------------------------------------------------------------------
def test_cache_hit_does_not_call_llm(db):
    # The autouse _no_real_llm fixture makes any LLM/payload call raise, so a
    # cache hit that avoids them is what lets this pass.
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA"])
    _add_report(db, user, "AAA", report_date=date.today(), score=77.0, bias="bullish")

    digest = wd.build_user_digest(user, db, max_stocks=10)

    assert digest["llm_calls"] == 0
    assert digest["cache_hits"] == 1
    assert digest["stocks"][0]["available"] is True
    assert digest["stocks"][0]["source"] == "cache"


# ----------------------------------------------------------------------------
# 5. Cost guard stops LLM calls once the budget is exhausted
# ----------------------------------------------------------------------------
def test_cost_guard_stops_llm_calls(db, monkeypatch):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA", "BBB"])  # neither has a cached report today

    calls: list[str] = []
    monkeypatch.setattr(wd, "generate_single_stock_report", _fake_generate(calls, score=80.0))
    monkeypatch.setattr(wd, "build_ai_payload", lambda ticker, db: {"ticker": ticker.upper(), "analysis_type": "swing_trade_research"})

    # Budget of 1: first ticker generates, second must fall back to unavailable.
    digest = wd.build_user_digest(user, db, max_stocks=10, llm_budget=1)

    assert digest["llm_calls"] == 1
    assert len(calls) == 1  # generate invoked exactly once
    available = [s for s in digest["stocks"] if s["available"]]
    unavailable = [s for s in digest["stocks"] if not s["available"]]
    assert len(available) == 1
    assert len(unavailable) == 1

    # Digest generation is recorded under the digest usage type (never the
    # on-demand "single_stock" quota).
    events = db.query(AIUsageEvent).all()
    assert len(events) == 1
    assert events[0].report_type == "watchlist_digest"


# ----------------------------------------------------------------------------
# 6. Empty watchlist -> no digest, no send
# ----------------------------------------------------------------------------
def test_empty_watchlist_returns_none(db):
    user = _make_user(db)
    assert wd.build_user_digest(user, db, max_stocks=10) is None


def test_job_empty_watchlist_sends_nothing(db, monkeypatch):
    user = _make_user(db)  # elite + active, but no watchlist

    sent: list[tuple] = []
    monkeypatch.setattr(job.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(job, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(job, "send_categorized_email", lambda *a, **k: sent.append((a, k)) or {"status": "sent"})

    summary = job.run_watchlist_digest(force=True)

    assert summary["ran"] is True
    assert summary["empty_watchlists"] == 1
    assert summary["emails_sent"] == 0
    assert sent == []


# ----------------------------------------------------------------------------
# Job-level guards
# ----------------------------------------------------------------------------
def test_job_email_disabled_is_hard_guard(db, monkeypatch):
    # EMAIL_ENABLED False must short-circuit BEFORE any DB/LLM work.
    monkeypatch.setattr(job.settings, "EMAIL_ENABLED", False)

    def _no_session():
        raise AssertionError("SessionLocal should not be opened when email is disabled")

    monkeypatch.setattr(job, "SessionLocal", _no_session)

    summary = job.run_watchlist_digest(force=True)

    assert summary["ran"] is False
    assert summary["reason"] == "email_disabled"
    assert summary["llm_calls"] == 0


def test_job_sends_digest_to_elite_user(db, monkeypatch):
    user = _make_user(db)
    _add_watchlist(db, user, ["AAA", "BBB"])
    today = date.today()
    _add_report(db, user, "AAA", report_date=today, score=82.0, bias="bullish")
    _add_report(db, user, "BBB", report_date=today, score=58.0, bias="neutral")

    captured: list[dict] = []

    def _fake_send(user_, category, subject, html, db_, *, preheader=None):
        captured.append({"category": category, "subject": subject, "html": html, "preheader": preheader})
        return {"status": "sent", "message_id": "m1"}

    monkeypatch.setattr(job.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(job, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(job, "send_categorized_email", _fake_send)

    summary = job.run_watchlist_digest(force=True)

    assert summary["emails_sent"] == 1
    assert summary["llm_calls"] == 0  # both served from cache
    assert len(captured) == 1
    assert captured[0]["category"] == "watchlist_digest"
    assert captured[0]["subject"].startswith("Your Watchlist Digest —")
    assert "Strongest setups" in captured[0]["html"]
    assert "AAA" in captured[0]["html"]


def test_job_skips_non_elite_users(db, monkeypatch):
    _make_user(db, tier="pro")
    _make_user(db, tier="elite", is_active=False)

    captured: list = []
    monkeypatch.setattr(job.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(job, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(job, "send_categorized_email", lambda *a, **k: captured.append(a) or {"status": "sent"})

    summary = job.run_watchlist_digest(force=True)

    assert summary["users_considered"] == 0
    assert summary["emails_sent"] == 0
    assert captured == []
