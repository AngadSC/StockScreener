from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai import market_context, ohlcv_backfill, payload_builder
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


def _seed_ticker(db: Session) -> Ticker:
    ticker = Ticker(id=1, symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
    db.add(ticker)
    db.commit()
    return ticker


def _seed_db_candles(db: Session, ticker: Ticker, days: list[date]) -> None:
    for index, candle_date in enumerate(days):
        close = 100.0 + index
        db.add(
            DailyOHLCV(
                ticker_id=ticker.id,
                date=candle_date,
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1_000_000 + index,
            )
        )
    db.commit()


def _mock_news(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        payload_builder,
        "get_recent_stock_news",
        lambda _ticker: {
            "provider_used": "none",
            "article_count": 0,
            "articles": [],
            "data_quality": {
                "available": False,
                "latest_article_date": None,
                "warnings": [],
            },
        },
    )


def test_ai_payload_backfills_missing_ohlcv_and_rebuilds_context_from_db(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = _seed_ticker(sqlite_db)
    all_days = get_trading_days_between(date(2025, 11, 14), date(2026, 5, 8))
    existing_days = all_days[:-5]
    missing_days = all_days[-5:]
    _seed_db_candles(sqlite_db, ticker, existing_days)
    monkeypatch.setattr(market_context, "_today", lambda: date(2026, 5, 10))
    _mock_news(monkeypatch)

    history = pd.DataFrame(
        [
            {
                "Open": 300.0 + index,
                "High": 302.0 + index,
                "Low": 299.0 + index,
                "Close": 301.0 + index,
                "Volume": 2_000_000 + index,
            }
            for index, _day in enumerate(missing_days)
        ],
        index=pd.to_datetime(missing_days),
    )
    calls: list[dict[str, Any]] = []

    class FakeTicker:
        def __init__(self, symbol: str) -> None:
            calls.append({"symbol": symbol})

        def history(self, **kwargs: Any) -> pd.DataFrame:
            calls[-1]["history_kwargs"] = kwargs
            return history

    monkeypatch.setattr(ohlcv_backfill.yf, "Ticker", FakeTicker)

    payload = payload_builder.build_ai_payload("aapl", sqlite_db)

    final_rows = (
        sqlite_db.query(DailyOHLCV)
        .filter(DailyOHLCV.ticker_id == ticker.id)
        .order_by(DailyOHLCV.date.asc())
        .all()
    )
    inserted_rows = [row for row in final_rows if row.date in missing_days]
    data_quality = payload["data_quality"]
    candles = payload["price_history"]["candles"]

    assert calls == [
        {
            "symbol": "AAPL",
            "history_kwargs": {
                "period": "1y",
                "interval": "1d",
                "auto_adjust": False,
                "actions": False,
            },
        }
    ]
    assert len(final_rows) == len(all_days) == 120
    assert [row.date for row in inserted_rows] == missing_days
    assert [row.close for row in inserted_rows] == [301.0 + index for index in range(5)]

    assert payload["price_history"]["available_candle_count"] == 120
    assert payload["price_history"]["lookback_candle_count"] == 120
    assert [candle["date"] for candle in candles] == [day.isoformat() for day in all_days]
    assert candles[-1] == {
        "date": "2026-05-08",
        "open": 304,
        "high": 306,
        "low": 303,
        "close": 305,
        "volume": 2_000_004,
    }
    assert payload["technical_summary"]["latest_candle"]["date"] == candles[-1]["date"]
    assert payload["technical_summary"]["latest_candle"]["close"] == candles[-1]["close"]
    assert payload["technical_summary"]["latest_candle"]["volume"] == candles[-1]["volume"]
    assert payload["volume_summary"]["latest_volume"] == 2_000_004

    assert data_quality["source"] == "database_after_optional_backfill"
    assert data_quality["initial_candle_count"] == len(existing_days)
    assert data_quality["final_candle_count"] == len(all_days)
    assert data_quality["price_history_candle_count"] == len(all_days)
    assert data_quality["yfinance_used"] is True
    assert data_quality["yfinance_fetched_count"] == 5
    assert data_quality["yfinance_valid_count"] == 5
    assert data_quality["yfinance_dropped_count"] == 0
    assert data_quality["inserted_rows"] == 5
    assert data_quality["updated_rows"] == 0
    assert "latest_candle_stale" in data_quality["initial_quality_reasons"]
    assert "missing_recent_trading_days" in data_quality["initial_quality_reasons"]
    assert data_quality["latest_candle_date"] == "2026-05-08"
    assert data_quality["missing_dates"] == []
    assert data_quality["final_quality_reasons"] == []
    assert data_quality["errors"] == []
