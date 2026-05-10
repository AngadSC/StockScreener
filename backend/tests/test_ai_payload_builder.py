from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai import market_context, payload_builder
from app.database.models import DailyOHLCV, Ticker
from app.utils.market_calendar import get_trading_days_between


@pytest.fixture
def sqlite_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Ticker.__table__.create(engine)
    DailyOHLCV.__table__.create(engine)
    _create_stock_fundamentals_table(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _create_stock_fundamentals_table(engine: Any) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE stock_fundamentals (
                    ticker_id SMALLINT PRIMARY KEY,
                    pe_ratio REAL,
                    forward_pe REAL,
                    peg_ratio REAL,
                    price_to_book REAL,
                    price_to_sales REAL,
                    ev_to_ebitda REAL,
                    profit_margin REAL,
                    operating_margin REAL,
                    roe REAL,
                    roa REAL,
                    debt_to_equity REAL,
                    current_ratio REAL,
                    quick_ratio REAL,
                    revenue_growth REAL,
                    earnings_growth REAL,
                    dividend_yield REAL,
                    dividend_rate REAL,
                    payout_ratio REAL,
                    market_cap BIGINT,
                    volume BIGINT,
                    avg_volume BIGINT,
                    beta REAL,
                    current_price REAL,
                    day_change_percent REAL,
                    fifty_two_week_high REAL,
                    fifty_two_week_low REAL,
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    additional_data JSON,
                    last_updated DATETIME
                )
                """
            )
        )


def _seed_ticker(sqlite_db: Session) -> Ticker:
    ticker = Ticker(id=1, symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
    sqlite_db.add(ticker)
    sqlite_db.commit()
    return ticker


def _seed_complete_candles(sqlite_db: Session, ticker: Ticker) -> list[date]:
    days = get_trading_days_between(date(2025, 10, 2), date(2026, 5, 8))
    for index, candle_date in enumerate(days):
        close = 100.0 + index
        sqlite_db.add(
            DailyOHLCV(
                ticker_id=ticker.id,
                date=candle_date,
                open=close - 0.75,
                high=close + 1.25,
                low=close - 1.5,
                close=close,
                volume=1_000_000 + (index * 1_000),
            )
        )
    sqlite_db.commit()
    return days


def _payload(sqlite_db: Session, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    ticker = _seed_ticker(sqlite_db)
    _seed_complete_candles(sqlite_db, ticker)
    monkeypatch.setattr(market_context, "_today", lambda: date(2026, 5, 10))
    monkeypatch.setattr(
        payload_builder,
        "get_recent_stock_news",
        lambda _ticker: {
            "provider_used": "newsapi",
            "article_count": 1,
            "articles": [
                {
                    "title": "Apple shares rise",
                    "source": "Example News",
                    "published_at": "2026-05-08T13:00:00Z",
                    "url": "https://example.com/aapl",
                    "summary": "Shares gain on market strength.",
                    "sentiment": "positive",
                }
            ],
            "data_quality": {
                "available": True,
                "latest_article_date": "2026-05-08T13:00:00Z",
                "warnings": [],
            },
        },
    )

    def fail_fetch(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("complete DB candles should not trigger yfinance")

    monkeypatch.setattr(market_context, "fetch_yfinance_daily_history", fail_fetch)
    return payload_builder.build_ai_payload("aapl", sqlite_db)


def test_build_ai_payload_includes_last_120_candles(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(sqlite_db, monkeypatch)

    price_history = payload["price_history"]
    candles = price_history["candles"]
    assert len(candles) == 120
    assert price_history["lookback_candle_count"] == 120
    assert price_history["latest_candle"] == candles[-1]
    assert candles[-1]["date"] == "2026-05-08"
    assert candles[-1]["open"] is not None
    assert candles[-1]["high"] is not None
    assert candles[-1]["low"] is not None
    assert candles[-1]["close"] is not None
    assert candles[-1]["volume"] is not None


def test_build_ai_payload_includes_data_quality(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(sqlite_db, monkeypatch)

    data_quality = payload["data_quality"]
    assert data_quality["source"] == "database_after_optional_backfill"
    assert data_quality["price_history_candle_count"] == 120
    assert data_quality["price_history_lookback_limit"] == 120
    assert data_quality["final_quality_reasons"] == []
    assert data_quality["yfinance_used"] is False
    assert data_quality["news_article_count"] == 1


def test_build_ai_payload_includes_technical_and_volume_summaries(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(sqlite_db, monkeypatch)

    technical_summary = payload["technical_summary"]
    volume_summary = payload["volume_summary"]
    assert technical_summary["latest_candle"]["date"] == "2026-05-08"
    assert technical_summary["sma_20"] is not None
    assert technical_summary["sma_50"] is not None
    assert technical_summary["rsi_14"] is not None
    assert technical_summary["trend"] != "insufficient_data"
    assert volume_summary["latest_volume"] is not None
    assert volume_summary["average_volume_20d"] is not None
    assert volume_summary["latest_volume_vs_average_volume_20d"] is not None
    assert volume_summary["volume_trend"] in {"elevated", "light", "normal"}


def test_build_ai_payload_represents_missing_fundamentals_without_crashing(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(sqlite_db, monkeypatch)

    assert payload["company_profile"]["name"] == "Apple Inc."
    assert payload["company_profile"]["exchange"] == "NASDAQ"
    assert payload["fundamental_summary"] == {
        "available": False,
        "missing_reason": "No fundamentals found in the database for this ticker.",
        "last_updated": None,
        "metrics": {},
    }
    assert payload["valuation_summary"] == {
        "available": False,
        "missing_reason": "No valuation fundamentals found in the database for this ticker.",
        "metrics": {},
    }
