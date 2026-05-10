from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai import market_context
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


def _ticker(db: Session) -> Ticker:
    ticker = Ticker(id=1, symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
    db.add(ticker)
    db.commit()
    return ticker


def _add_candle(
    db: Session,
    ticker: Ticker,
    candle_date: date,
    *,
    close: float,
    volume: int = 1_000_000,
) -> None:
    db.add(
        DailyOHLCV(
            ticker_id=ticker.id,
            date=candle_date,
            open=close - 1.0,
            high=close + 1.0,
            low=close - 2.0,
            close=close,
            volume=volume,
        )
    )


def _seed_candles(db: Session, ticker: Ticker, days: list[date]) -> None:
    for index, candle_date in enumerate(days):
        _add_candle(db, ticker, candle_date, close=100.0 + index)
    db.commit()


def _yf_candle(candle_date: date, close: float) -> dict[str, object]:
    return {
        "date": candle_date,
        "open": close - 1.0,
        "high": close + 1.0,
        "low": close - 2.0,
        "close": close,
        "volume": 1_500_000,
    }


def test_build_market_context_uses_complete_db_candles_without_yfinance(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = _ticker(sqlite_db)
    days = get_trading_days_between(date(2026, 2, 2), date(2026, 5, 8))
    _seed_candles(sqlite_db, ticker, days)
    monkeypatch.setattr(market_context, "_today", lambda: date(2026, 5, 10))

    def fail_fetch(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("yfinance should not be used for complete DB candles")

    monkeypatch.setattr(market_context, "fetch_yfinance_daily_history", fail_fetch)

    context = market_context.build_market_context("aapl", sqlite_db)

    market_data = context["market_data"]
    data_quality = market_data["data_quality"]
    assert len(market_data["historical_ohlcv"]) == len(days)
    assert market_data["latest_db_date"] == "2026-05-08"
    assert market_data["current"]["source"] == "database"
    assert market_data["current"]["current_price"] == 100.0 + len(days) - 1
    assert data_quality["initial_candle_count"] == len(days)
    assert data_quality["final_candle_count"] == len(days)
    assert data_quality["yfinance_used"] is False
    assert data_quality["inserted_rows"] == 0
    assert data_quality["updated_rows"] == 0
    assert data_quality["warnings"] == []
    assert data_quality["errors"] == []


def test_build_market_context_backfills_stale_db_candles_before_building_context(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = _ticker(sqlite_db)
    existing_days = get_trading_days_between(date(2026, 2, 2), date(2026, 5, 1))
    _seed_candles(sqlite_db, ticker, existing_days)
    monkeypatch.setattr(market_context, "_today", lambda: date(2026, 5, 10))

    all_days = get_trading_days_between(date(2026, 2, 2), date(2026, 5, 8))
    yf_candles = [_yf_candle(candle_date, 200.0 + index) for index, candle_date in enumerate(all_days)]

    def fake_fetch(ticker_symbol: str, period: str = "1y") -> dict[str, Any]:
        assert ticker_symbol == "AAPL"
        assert period == "1y"
        return {
            "provider": "yfinance",
            "interval": "1d",
            "ticker": ticker_symbol,
            "period": period,
            "fetched_count": len(yf_candles),
            "valid_count": len(yf_candles),
            "dropped_count": 0,
            "error": None,
            "candles": yf_candles,
        }

    monkeypatch.setattr(market_context, "fetch_yfinance_daily_history", fake_fetch)

    context = market_context.build_market_context("AAPL", sqlite_db)

    final_rows = sqlite_db.query(DailyOHLCV).filter(DailyOHLCV.ticker_id == ticker.id).all()
    market_data = context["market_data"]
    data_quality = market_data["data_quality"]
    assert len(final_rows) == len(all_days)
    assert len(market_data["historical_ohlcv"]) == len(all_days)
    assert market_data["latest_db_date"] == "2026-05-08"
    assert market_data["current"]["as_of"] == "2026-05-08"
    assert market_data["current"]["current_price"] == 200.0 + len(all_days) - 1
    assert data_quality["initial_candle_count"] == len(existing_days)
    assert data_quality["final_candle_count"] == len(all_days)
    assert data_quality["yfinance_used"] is True
    assert data_quality["inserted_rows"] == len(all_days) - len(existing_days)
    assert data_quality["updated_rows"] == 0
    assert data_quality["latest_candle_date"] == "2026-05-08"
    assert data_quality["errors"] == []
    assert data_quality["final_quality_reasons"] == []


def test_build_market_context_reports_yfinance_fetch_errors(
    sqlite_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = _ticker(sqlite_db)
    existing_days = get_trading_days_between(date(2026, 2, 2), date(2026, 5, 1))
    _seed_candles(sqlite_db, ticker, existing_days)
    monkeypatch.setattr(market_context, "_today", lambda: date(2026, 5, 10))
    monkeypatch.setattr(
        market_context,
        "fetch_yfinance_daily_history",
        lambda *_args, **_kwargs: {
            "fetched_count": 0,
            "valid_count": 0,
            "dropped_count": 0,
            "error": "provider unavailable",
            "candles": [],
        },
    )

    context = market_context.build_market_context("AAPL", sqlite_db)

    data_quality = context["market_data"]["data_quality"]
    assert data_quality["yfinance_used"] is True
    assert data_quality["inserted_rows"] == 0
    assert data_quality["updated_rows"] == 0
    assert data_quality["errors"] == ["provider unavailable"]
    assert data_quality["final_candle_count"] == len(existing_days)
    assert "latest_candle_stale" in data_quality["final_quality_reasons"]
