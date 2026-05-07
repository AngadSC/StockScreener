from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.market_context import build_market_context
from app.ai.news_client import get_recent_stock_news
from app.ai.schemas import AIReportInput


def build_ai_payload(ticker: str, db: Session) -> dict:
    ticker = ticker.strip().upper()
    context = build_market_context(ticker, db)
    payload = {
        "ticker": ticker,
        "analysis_type": "swing_trade_research",
        "timeframe": "3-20 trading days",
        "market_data": context.get("market_data", {}),
        "technical_data": context.get("technical_data", {}),
        "fundamental_data": context.get("fundamental_data", {}),
        "valuation_data": context.get("valuation_data", {}),
        "news_data": get_recent_stock_news(ticker),
        "constraints": {
            "do_not_invent_data": True,
            "use_only_provided_data": True,
        },
    }
    return AIReportInput.model_validate(payload).model_dump(mode="json")
