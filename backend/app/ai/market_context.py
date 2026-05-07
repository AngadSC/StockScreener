from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import yfinance as yf
from sqlalchemy import and_
from sqlalchemy.orm import Session

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


def _latest_yfinance_snapshot(ticker: str) -> dict[str, Any]:
    snapshot = {
        "current_price": None,
        "today_open": None,
        "today_high": None,
        "today_low": None,
        "today_close": None,
        "current_volume": None,
        "day_change_percent": None,
        "as_of": None,
        "source": "yfinance",
    }

    try:
        history = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
    except Exception as exc:
        snapshot["error"] = str(exc)
        return snapshot

    if history is None or history.empty:
        return snapshot

    latest = history.iloc[-1]
    previous_close = None
    if len(history) > 1:
        previous_close = _round(history.iloc[-2].get("Close"))

    current_price = _round(latest.get("Close"))
    day_change_percent = None
    if current_price is not None and previous_close not in (None, 0):
        day_change_percent = ((current_price - previous_close) / previous_close) * 100

    latest_index = history.index[-1]
    latest_volume = latest.get("Volume")
    snapshot.update(
        {
            "current_price": current_price,
            "today_open": _round(latest.get("Open")),
            "today_high": _round(latest.get("High")),
            "today_low": _round(latest.get("Low")),
            "today_close": _round(latest.get("Close")),
            "current_volume": int(latest_volume)
            if latest_volume is not None and latest_volume == latest_volume
            else None,
            "day_change_percent": _round(day_change_percent),
            "as_of": _iso(latest_index),
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


def build_market_context(ticker: str, db: Session) -> dict:
    ticker = ticker.strip().upper()
    end_date = date.today()
    start_date = end_date - timedelta(days=220)

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    prices: list[DailyOHLCV] = []
    fundamentals = None
    if ticker_obj:
        prices = (
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
        fundamentals = (
            db.query(StockFundamental).filter(StockFundamental.ticker_id == ticker_obj.id).first()
        )

    closes = [float(row.close) for row in prices if row.close is not None]
    volumes = [int(row.volume) for row in prices if row.volume is not None]
    recent_30 = prices[-30:]
    support = min((row.low for row in recent_30 if row.low is not None), default=None)
    resistance = max((row.high for row in recent_30 if row.high is not None), default=None)
    latest_db_price = prices[-1] if prices else None
    yfinance_snapshot = _latest_yfinance_snapshot(ticker)
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
        "historical_ohlcv": historical_ohlcv,
        "latest_db_close": _round(latest_db_price.close) if latest_db_price else None,
        "latest_db_date": latest_db_price.date.isoformat() if latest_db_price else None,
        "current": yfinance_snapshot,
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
        "generated_at": datetime.utcnow().isoformat(),
        "market_data": market_data,
        "technical_data": technical_data,
        "fundamental_data": fundamental_data,
        "valuation_data": valuation_data,
    }
