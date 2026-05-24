from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.market_context import build_market_context
from app.ai.news_client import get_recent_stock_news
from app.ai.schemas import AIReportInput
from app.ai.scoring import build_deterministic_scores
from app.ai.technical_summary import build_technical_summary
from app.ai.trade_levels import build_trade_levels


PRICE_HISTORY_LOOKBACK_CANDLES = 120


def _round(value: Any, digits: int = 4) -> float | int | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    rounded = round(numeric, digits)
    return int(rounded) if rounded.is_integer() else rounded


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _clean_candle(candle: dict[str, Any]) -> dict[str, Any]:
    volume = candle.get("volume")
    try:
        clean_volume = int(volume) if volume is not None else None
    except (TypeError, ValueError):
        clean_volume = None

    return {
        "date": candle.get("date"),
        "open": _round(candle.get("open")),
        "high": _round(candle.get("high")),
        "low": _round(candle.get("low")),
        "close": _round(candle.get("close")),
        "volume": clean_volume,
    }


def _company_profile(
    ticker: str,
    market_data: dict[str, Any],
    fundamental_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "name": market_data.get("name"),
        "exchange": market_data.get("exchange"),
        "sector": fundamental_data.get("sector"),
        "industry": fundamental_data.get("industry"),
    }


def _technical_summary(candles: list[dict[str, Any]]) -> dict[str, Any]:
    summary = build_technical_summary(candles)
    return {
        "latest_candle": summary.get("latest_candle"),
        "trend": summary.get("trend"),
        "sma_20": summary.get("sma_20"),
        "sma_50": summary.get("sma_50"),
        "sma_200": summary.get("sma_200"),
        "rsi_14": summary.get("rsi_14"),
        "atr_14": summary.get("atr_14"),
        "returns": {
            "return_5d": summary.get("return_5d"),
            "return_10d": summary.get("return_10d"),
            "return_20d": summary.get("return_20d"),
            "return_60d": summary.get("return_60d"),
        },
        "price_levels": {
            "high_20d": summary.get("high_20d"),
            "low_20d": summary.get("low_20d"),
            "high_60d": summary.get("high_60d"),
            "low_60d": summary.get("low_60d"),
            "support_20d": summary.get("20d_support"),
            "resistance_20d": summary.get("20d_resistance"),
            "distance_from_support_20d": summary.get("20d_distance_from_support"),
            "distance_from_resistance_20d": summary.get("20d_distance_from_resistance"),
        },
        "price_action_structure": summary.get("price_action_structure"),
        "moving_average_distances": {
            "distance_from_sma_20": summary.get("distance_from_sma_20"),
            "distance_from_sma_50": summary.get("distance_from_sma_50"),
            "distance_from_sma_200": summary.get("distance_from_sma_200"),
        },
    }


def _volume_trend(summary: dict[str, Any]) -> str:
    ratio = summary.get("latest_volume_vs_average_volume_20d")
    if ratio is None:
        return "insufficient_data"
    if ratio >= 1.5:
        return "elevated"
    if ratio <= 0.7:
        return "light"
    return "normal"


def _volume_summary(candles: list[dict[str, Any]]) -> dict[str, Any]:
    summary = build_technical_summary(candles)
    latest_candle = summary.get("latest_candle") or {}
    return {
        "latest_volume": latest_candle.get("volume"),
        "average_volume_20d": summary.get("average_volume_20d"),
        "average_volume_30d": summary.get("average_volume_30d"),
        "average_volume_50d": summary.get("average_volume_50d"),
        "latest_volume_vs_average_volume_20d": summary.get("latest_volume_vs_average_volume_20d"),
        "relative_volume_1d": summary.get("relative_volume_1d"),
        "relative_volume_5d": summary.get("relative_volume_5d"),
        "up_day_volume_avg_20d": summary.get("up_day_volume_avg_20d"),
        "down_day_volume_avg_20d": summary.get("down_day_volume_avg_20d"),
        "up_down_volume_ratio": summary.get("up_down_volume_ratio"),
        "volume_dry_up_near_support": summary.get("volume_dry_up_near_support"),
        "breakout_volume_confirmed": summary.get("breakout_volume_confirmed"),
        "distribution_days_20d": summary.get("distribution_days_20d"),
        "accumulation_days_20d": summary.get("accumulation_days_20d"),
        "obv_trend": summary.get("obv_trend"),
        "volume_price_confirmation": summary.get("volume_price_confirmation"),
        "volume_trend": _volume_trend(summary),
    }


def _fundamental_summary(fundamental_data: dict[str, Any]) -> dict[str, Any]:
    if not fundamental_data:
        return {
            "available": False,
            "missing_reason": "No fundamentals found in the database for this ticker.",
            "last_updated": None,
            "metrics": {},
        }

    return {
        "available": True,
        "missing_reason": None,
        "last_updated": fundamental_data.get("last_updated"),
        "metrics": {
            "market_cap": fundamental_data.get("market_cap"),
            "beta": fundamental_data.get("beta"),
            "profit_margin": fundamental_data.get("profit_margin"),
            "operating_margin": fundamental_data.get("operating_margin"),
            "roe": fundamental_data.get("roe"),
            "roa": fundamental_data.get("roa"),
            "debt_to_equity": fundamental_data.get("debt_to_equity"),
            "current_ratio": fundamental_data.get("current_ratio"),
            "quick_ratio": fundamental_data.get("quick_ratio"),
            "revenue_growth": fundamental_data.get("revenue_growth"),
            "earnings_growth": fundamental_data.get("earnings_growth"),
            "dividend_yield": fundamental_data.get("dividend_yield"),
            "dividend_rate": fundamental_data.get("dividend_rate"),
            "payout_ratio": fundamental_data.get("payout_ratio"),
        },
    }


def _valuation_summary(valuation_data: dict[str, Any]) -> dict[str, Any]:
    if not valuation_data:
        return {
            "available": False,
            "missing_reason": "No valuation fundamentals found in the database for this ticker.",
            "metrics": {},
        }

    return {
        "available": True,
        "missing_reason": None,
        "metrics": {
            "pe_ratio": valuation_data.get("pe_ratio"),
            "forward_pe": valuation_data.get("forward_pe"),
            "peg_ratio": valuation_data.get("peg_ratio"),
            "price_to_book": valuation_data.get("price_to_book"),
            "price_to_sales": valuation_data.get("price_to_sales"),
            "ev_to_ebitda": valuation_data.get("ev_to_ebitda"),
            "fifty_two_week_high": valuation_data.get("fifty_two_week_high"),
            "fifty_two_week_low": valuation_data.get("fifty_two_week_low"),
        },
    }


def _data_quality(
    source_quality: dict[str, Any],
    *,
    candles: list[dict[str, Any]],
    fundamental_summary: dict[str, Any],
    valuation_summary: dict[str, Any],
    news_payload: dict[str, Any],
) -> dict[str, Any]:
    quality = dict(source_quality)
    quality.update(
        {
            "source": "database_after_optional_backfill",
            "price_history_candle_count": len(candles),
            "price_history_lookback_limit": PRICE_HISTORY_LOOKBACK_CANDLES,
            "has_fundamentals": bool(fundamental_summary.get("available")),
            "has_valuation": bool(valuation_summary.get("available")),
            "news_article_count": news_payload.get("article_count", 0),
        }
    )
    return quality


def summarize_ai_payload_for_logs(payload: dict) -> dict[str, Any]:
    price_history = payload.get("price_history") if isinstance(payload, dict) else {}
    if not isinstance(price_history, dict):
        price_history = {}

    latest_candle = price_history.get("latest_candle")
    if not isinstance(latest_candle, dict):
        latest_candle = {}

    data_quality = payload.get("data_quality") if isinstance(payload, dict) else {}
    if not isinstance(data_quality, dict):
        data_quality = {}

    fundamental_summary = payload.get("fundamental_summary") if isinstance(payload, dict) else {}
    if not isinstance(fundamental_summary, dict):
        fundamental_summary = {}

    valuation_summary = payload.get("valuation_summary") if isinstance(payload, dict) else {}
    if not isinstance(valuation_summary, dict):
        valuation_summary = {}

    news = payload.get("news") if isinstance(payload, dict) else {}
    if not isinstance(news, dict):
        news = {}

    technical_summary = payload.get("technical_summary") if isinstance(payload, dict) else {}

    return {
        "ticker": payload.get("ticker") if isinstance(payload, dict) else None,
        "candle_count": price_history.get("lookback_candle_count"),
        "available_candle_count": price_history.get("available_candle_count"),
        "latest_candle_date": latest_candle.get("date") or data_quality.get("latest_candle_date"),
        "yfinance_backfill_used": bool(data_quality.get("yfinance_used")),
        "inserted_candle_count": _int_or_zero(data_quality.get("inserted_rows")),
        "updated_candle_count": _int_or_zero(data_quality.get("updated_rows")),
        "fundamental_available": bool(fundamental_summary.get("available")),
        "valuation_available": bool(valuation_summary.get("available")),
        "news_article_count": _int_or_zero(news.get("article_count") or data_quality.get("news_article_count")),
        "technical_summary_available": bool(technical_summary),
    }


def build_ai_payload(ticker: str, db: Session) -> dict:
    ticker = ticker.strip().upper()
    context = build_market_context(ticker, db)
    market_data = context.get("market_data", {})
    all_candles = [_clean_candle(candle) for candle in market_data.get("historical_ohlcv", [])]
    candles = all_candles[-PRICE_HISTORY_LOOKBACK_CANDLES:]
    latest_candle = candles[-1] if candles else None
    technical_summary = _technical_summary(all_candles)
    volume_summary = _volume_summary(all_candles)
    fundamental_summary = _fundamental_summary(context.get("fundamental_data", {}))
    valuation_summary = _valuation_summary(context.get("valuation_data", {}))
    news_payload = get_recent_stock_news(ticker)
    data_quality = _data_quality(
        market_data.get("data_quality", {}),
        candles=candles,
        fundamental_summary=fundamental_summary,
        valuation_summary=valuation_summary,
        news_payload=news_payload,
    )
    deterministic_scores = build_deterministic_scores(
        technical_summary=technical_summary,
        volume_summary=volume_summary,
        fundamental_summary=fundamental_summary,
        valuation_summary=valuation_summary,
        news=news_payload,
        data_quality=data_quality,
    )
    deterministic_scores["trade_levels"] = build_trade_levels(technical_summary, deterministic_scores)

    payload = {
        "ticker": ticker,
        "analysis_type": "swing_trade_research",
        "timeframe": "3-20 trading days",
        "generated_at": context.get("generated_at"),
        "company_profile": _company_profile(ticker, market_data, context.get("fundamental_data", {})),
        "price_history": {
            "candles": candles,
            "latest_candle": latest_candle,
            "lookback_candle_count": len(candles),
            "available_candle_count": len(all_candles),
        },
        "technical_summary": technical_summary,
        "volume_summary": volume_summary,
        "fundamental_summary": fundamental_summary,
        "valuation_summary": valuation_summary,
        "news": news_payload,
        "data_quality": data_quality,
        "deterministic_scores": deterministic_scores,
        "constraints": {
            "do_not_invent_data": True,
            "use_only_provided_data": True,
            "score_fields_are_computed_in_code": True,
            "ai_must_explain_scores_not_create_them": True,
            "use_price_history_for_entry_analysis": True,
            "output_is_research_not_financial_advice": True,
        },
    }
    return AIReportInput.model_validate(payload).model_dump(mode="json")
