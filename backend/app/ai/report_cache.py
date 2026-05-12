from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database.models import AIStockReport
from app.services.cache import cache_service

REPORT_CACHE_TTL_SECONDS = 4 * 60 * 60


def _cache_key(user_id: str, ticker: str) -> str:
    return f"ai_report:{user_id}:{ticker.strip().upper()}:{date.today().isoformat()}"


def _report_cache_payload(report: AIStockReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "user_id": report.user_id,
        "ticker": report.ticker,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "tier_used": report.tier_used,
        "report_type": report.report_type,
        "ai_report": report.ai_report,
        "input_snapshot": report.input_snapshot,
        "sources": report.sources,
    }


def get_fresh_report(user_id: str, ticker: str, db: Session) -> AIStockReport | None:
    ticker = ticker.strip().upper()
    cache_key = _cache_key(user_id, ticker)
    cached = cache_service.get(cache_key)
    if cached and cached.get("id"):
        report = db.query(AIStockReport).filter(AIStockReport.id == cached["id"]).first()
        if report:
            return report

    cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
    report = (
        db.query(AIStockReport)
        .filter(
            and_(
                AIStockReport.user_id == int(user_id),
                AIStockReport.ticker == ticker,
                AIStockReport.created_at >= cutoff,
            )
        )
        .order_by(AIStockReport.created_at.desc())
        .first()
    )
    if report:
        cache_service.set(cache_key, _report_cache_payload(report), ttl=REPORT_CACHE_TTL_SECONDS)
        return report

    return None


def save_report(
    user_id: str,
    ticker: str,
    payload: dict,
    ai_response: dict,
    tier_used: str,
    db: Session,
) -> AIStockReport:
    ticker = ticker.strip().upper()
    report = AIStockReport(
        user_id=int(user_id),
        ticker=ticker,
        report_date=date.today(),
        tier_used=tier_used,
        report_type=payload.get("analysis_type", "single_stock"),
        swing_bias=ai_response.get("directional_bias") or ai_response.get("swing_bias"),
        setup_type=ai_response.get("setup_type"),
        setup_quality_score=ai_response.get("setup_quality_score"),
        entry_timing_score=ai_response.get("entry_timing_score"),
        technical_score=ai_response.get("technical_score"),
        fundamental_score=ai_response.get("fundamental_score"),
        sentiment_score=ai_response.get("sentiment_score"),
        valuation_score=ai_response.get("valuation_score"),
        risk_score=ai_response.get("risk_score"),
        ai_report=ai_response,
        input_snapshot=payload,
        sources={"market_data": "database+yfinance", "news_data": "newsapi_or_yfinance"},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    cache_service.set(_cache_key(user_id, ticker), _report_cache_payload(report), ttl=REPORT_CACHE_TTL_SECONDS)
    return report
