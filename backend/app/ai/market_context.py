from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.ai.ohlcv_backfill import backfill_daily_ohlcv_from_candles, fetch_yfinance_daily_history
from app.ai.ohlcv_quality import assess_ohlcv_quality
from app.database.models import DailyOHLCV, StockFundamental, Ticker


def _round(value: Any, digits: int = 4) -> float | int | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return round(numeric, digits)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _sma(values: list[float], window: int) -> float | None:
    clean = [float(value) for value in values[-window:] if value is not None]
    if len(clean) < window:
        return None
    return sum(clean) / window


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None

    recent = values[-(period + 1) :]
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(recent, recent[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _today() -> date:
    return date.today()


def _latest_db_snapshot(prices: list[DailyOHLCV]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "current_price": None,
        "today_open": None,
        "today_high": None,
        "today_low": None,
        "today_close": None,
        "current_volume": None,
        "day_change_percent": None,
        "as_of": None,
        "source": "database",
    }

    if not prices:
        return snapshot

    latest = prices[-1]
    previous = prices[-2] if len(prices) > 1 else None
    previous_close = _round(previous.close) if previous is not None else None

    current_price = _round(latest.close)
    day_change_percent = None
    if current_price is not None and previous_close not in (None, 0):
        day_change_percent = ((current_price - previous_close) / previous_close) * 100

    snapshot.update(
        {
            "current_price": current_price,
            "today_open": _round(latest.open),
            "today_high": _round(latest.high),
            "today_low": _round(latest.low),
            "today_close": _round(latest.close),
            "current_volume": int(latest.volume) if latest.volume is not None else None,
            "day_change_percent": _round(day_change_percent),
            "as_of": _iso(latest.date),
        }
    )
    return snapshot


def _fundamental_blocks(fundamentals: StockFundamental | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if fundamentals is None:
        return {}, {}

    fundamental_data = {
        "sector": fundamentals.sector,
        "industry": fundamentals.industry,
        "market_cap": fundamentals.market_cap,
        "beta": _round(fundamentals.beta),
        "profit_margin": _round(fundamentals.profit_margin),
        "operating_margin": _round(fundamentals.operating_margin),
        "roe": _round(fundamentals.roe),
        "roa": _round(fundamentals.roa),
        "debt_to_equity": _round(fundamentals.debt_to_equity),
        "current_ratio": _round(fundamentals.current_ratio),
        "quick_ratio": _round(fundamentals.quick_ratio),
        "revenue_growth": _round(fundamentals.revenue_growth),
        "earnings_growth": _round(fundamentals.earnings_growth),
        "dividend_yield": _round(fundamentals.dividend_yield),
        "dividend_rate": _round(fundamentals.dividend_rate),
        "payout_ratio": _round(fundamentals.payout_ratio),
        "last_updated": _iso(fundamentals.last_updated),
    }
    valuation_data = {
        "pe_ratio": _round(fundamentals.pe_ratio),
        "forward_pe": _round(fundamentals.forward_pe),
        "peg_ratio": _round(fundamentals.peg_ratio),
        "price_to_book": _round(fundamentals.price_to_book),
        "price_to_sales": _round(fundamentals.price_to_sales),
        "ev_to_ebitda": _round(fundamentals.ev_to_ebitda),
        "fifty_two_week_high": _round(fundamentals.fifty_two_week_high),
        "fifty_two_week_low": _round(fundamentals.fifty_two_week_low),
    }
    return fundamental_data, valuation_data


def _query_prices(
    db: Session,
    ticker_obj: Ticker,
    *,
    start_date: date,
    end_date: date,
) -> list[DailyOHLCV]:
    return (
        db.query(DailyOHLCV)
        .filter(
            and_(
                DailyOHLCV.ticker_id == ticker_obj.id,
                DailyOHLCV.date >= start_date,
                DailyOHLCV.date <= end_date,
            )
        )
        .order_by(DailyOHLCV.date.asc())
        .all()
    )


def _append_unique(target: list[str], values: list[Any]) -> None:
    for value in values:
        text = str(value)
        if text not in target:
            target.append(text)


def _build_data_quality(initial_quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_candle_count": initial_quality.get("initial_candle_count", 0),
        "final_candle_count": initial_quality.get("initial_candle_count", 0),
        "yfinance_used": False,
        "inserted_rows": 0,
        "updated_rows": 0,
        "latest_candle_date": initial_quality.get("latest_db_date"),
        "warnings": list(initial_quality.get("warnings") or []),
        "errors": [],
        "initial_quality_reasons": list(initial_quality.get("reasons") or []),
        "final_quality_reasons": list(initial_quality.get("reasons") or []),
        "missing_dates": list(initial_quality.get("missing_dates") or []),
        "invalid_candle_dates": list(initial_quality.get("invalid_candle_dates") or []),
        "yfinance_fetched_count": 0,
        "yfinance_valid_count": 0,
        "yfinance_dropped_count": 0,
    }


def _finalize_data_quality(data_quality: dict[str, Any], final_quality: dict[str, Any]) -> None:
    data_quality["final_candle_count"] = final_quality.get("initial_candle_count", 0)
    data_quality["latest_candle_date"] = final_quality.get("latest_db_date")
    data_quality["final_quality_reasons"] = list(final_quality.get("reasons") or [])
    data_quality["missing_dates"] = list(final_quality.get("missing_dates") or [])
    data_quality["invalid_candle_dates"] = list(final_quality.get("invalid_candle_dates") or [])
    _append_unique(data_quality["warnings"], final_quality.get("warnings") or [])


def _fill_ohlcv_gaps_from_yfinance(
    ticker: str,
    ticker_obj: Ticker | None,
    db: Session,
    prices: list[DailyOHLCV],
    *,
    start_date: date,
    end_date: date,
) -> tuple[list[DailyOHLCV], dict[str, Any]]:
    initial_quality = assess_ohlcv_quality(prices, as_of_date=end_date)
    data_quality = _build_data_quality(initial_quality)

    if not initial_quality.get("has_gaps"):
        return prices, data_quality

    if ticker_obj is None:
        data_quality["warnings"].append(
            "Ticker was not found in the database; yfinance backfill was skipped."
        )
        return prices, data_quality

    data_quality["yfinance_used"] = True
    fetched = fetch_yfinance_daily_history(ticker, period="1y")
    data_quality["yfinance_fetched_count"] = fetched.get("fetched_count", 0)
    data_quality["yfinance_valid_count"] = fetched.get("valid_count", 0)
    data_quality["yfinance_dropped_count"] = fetched.get("dropped_count", 0)

    if fetched.get("error"):
        data_quality["errors"].append(str(fetched["error"]))
    else:
        try:
            backfill_result = backfill_daily_ohlcv_from_candles(
                db,
                ticker_obj,
                fetched.get("candles") or [],
            )
            data_quality["inserted_rows"] = backfill_result.inserted_rows
            data_quality["updated_rows"] = backfill_result.updated_rows
            if backfill_result.inserted_rows or backfill_result.updated_rows:
                db.commit()
        except Exception as exc:
            db.rollback()
            data_quality["inserted_rows"] = 0
            data_quality["updated_rows"] = 0
            data_quality["errors"].append(str(exc))

    prices = _query_prices(db, ticker_obj, start_date=start_date, end_date=end_date)
    final_quality = assess_ohlcv_quality(prices, as_of_date=end_date)
    _finalize_data_quality(data_quality, final_quality)
    return prices, data_quality


def build_market_context(ticker: str, db: Session) -> dict:
    ticker = ticker.strip().upper()
    end_date = _today()
    start_date = end_date - timedelta(days=220)

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    prices: list[DailyOHLCV] = []
    fundamentals = None
    if ticker_obj:
        prices = _query_prices(db, ticker_obj, start_date=start_date, end_date=end_date)
        fundamentals = (
            db.query(StockFundamental).filter(StockFundamental.ticker_id == ticker_obj.id).first()
        )

    prices, data_quality = _fill_ohlcv_gaps_from_yfinance(
        ticker,
        ticker_obj,
        db,
        prices,
        start_date=start_date,
        end_date=end_date,
    )

    closes = [float(row.close) for row in prices if row.close is not None]
    volumes = [int(row.volume) for row in prices if row.volume is not None]
    recent_30 = prices[-30:]
    support = min((row.low for row in recent_30 if row.low is not None), default=None)
    resistance = max((row.high for row in recent_30 if row.high is not None), default=None)
    latest_db_price = prices[-1] if prices else None
    current_snapshot = _latest_db_snapshot(prices)
    fundamental_data, valuation_data = _fundamental_blocks(fundamentals)

    historical_ohlcv = [
        {
            "date": row.date.isoformat(),
            "open": _round(row.open),
            "high": _round(row.high),
            "low": _round(row.low),
            "close": _round(row.close),
            "volume": int(row.volume) if row.volume is not None else None,
        }
        for row in prices
    ]

    market_data = {
        "ticker": ticker,
        "name": ticker_obj.name if ticker_obj else None,
        "exchange": ticker_obj.exchange if ticker_obj else None,
        "historical_ohlcv": historical_ohlcv,
        "latest_db_close": _round(latest_db_price.close) if latest_db_price else None,
        "latest_db_date": latest_db_price.date.isoformat() if latest_db_price else None,
        "current": current_snapshot,
        "data_quality": data_quality,
    }
    technical_data = {
        "moving_average_20d": _round(_sma(closes, 20)),
        "moving_average_50d": _round(_sma(closes, 50)),
        "rsi_14": _round(_rsi(closes, 14)),
        "average_volume_30d": int(sum(volumes[-30:]) / 30) if len(volumes) >= 30 else None,
        "support": _round(support),
        "resistance": _round(resistance),
        "support_resistance_lookback_days": 30,
    }

    return {
        "ticker": ticker,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_data": market_data,
        "technical_data": technical_data,
        "fundamental_data": fundamental_data,
        "valuation_data": valuation_data,
    }
