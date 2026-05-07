from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.ai.llm_client import generate_single_stock_report
from app.ai.payload_builder import build_ai_payload
from app.ai.report_cache import get_fresh_report, save_report
from app.ai.schemas import AIReportResponse
from app.ai.usage_limits import check_usage_limit, record_usage_event
from app.config import settings
from app.database.connection import get_db
from app.database.models import AIStockReport, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/ai-reports", tags=["ai-reports"])

ALLOWED_AI_REPORT_TIERS = {"pro", "trader", "elite"}


def _normalize_tier(tier: str | None) -> str:
    return (tier or "free").strip().lower()


def _report_response(report: AIStockReport, cached: bool) -> AIReportResponse:
    created_at = report.created_at or datetime.now(timezone.utc)
    return AIReportResponse.model_validate(
        {
            "ticker": report.ticker,
            "created_at": created_at,
            "cached": cached,
            "tier_used": report.tier_used or "unknown",
            "report": report.ai_report or {},
        }
    )


def _pop_usage_metadata(ai_response: dict[str, Any]) -> dict[str, int | str]:
    usage = ai_response.pop("_usage", {})
    if not isinstance(usage, dict):
        usage = {}
    return {
        "model_used": str(usage.get("model_used") or settings.ai_model),
        "tokens_input": int(usage.get("tokens_input") or 0),
        "tokens_output": int(usage.get("tokens_output") or 0),
    }


@router.post("/{ticker}", response_model=AIReportResponse)
def create_ai_report(
    ticker: str = Path(..., min_length=1, max_length=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIReportResponse:
    ticker_symbol = ticker.strip().upper()
    if not ticker_symbol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticker is required.")

    tier = _normalize_tier(current_user.tier)

    if tier not in ALLOWED_AI_REPORT_TIERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI reports require a pro, trader, or elite account tier.",
        )

    user_id = str(current_user.id)
    check_usage_limit(user_id, db)

    cached_report = get_fresh_report(user_id, ticker_symbol, db)
    if cached_report:
        return _report_response(cached_report, cached=True)

    payload = build_ai_payload(ticker_symbol, db)
    ai_response = generate_single_stock_report(payload, user_id, ticker_symbol, db)
    usage = _pop_usage_metadata(ai_response)
    saved_report = save_report(user_id, ticker_symbol, payload, ai_response, tier, db)
    record_usage_event(
        user_id=user_id,
        ticker=ticker_symbol,
        model_used=str(usage["model_used"]),
        tokens_input=int(usage["tokens_input"]),
        tokens_output=int(usage["tokens_output"]),
        db=db,
    )

    return _report_response(saved_report, cached=False)
