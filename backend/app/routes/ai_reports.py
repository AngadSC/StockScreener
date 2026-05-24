from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.ai.llm_client import generate_single_stock_report
from app.ai.payload_builder import build_ai_payload, summarize_ai_payload_for_logs
from app.ai.report_cache import get_fresh_report, save_report
from app.ai.schemas import AIReportOutput, AIReportResponse
from app.ai.usage_limits import check_usage_limit, record_usage_event
from app.config import settings
from app.database.connection import get_db
from app.database.models import AIStockReport, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/ai-reports", tags=["ai-reports"])
logger = logging.getLogger(__name__)

ALLOWED_AI_REPORT_TIERS = {"pro", "trader", "elite"}
LEGACY_ACTIONABLE_REPORT_DEFAULTS: dict[str, Any] = {
    "action_label": "neutral_wait",
    "directional_bias": "neutral",
    "timeframe_ratings": {
        "short_term": {
            "rating": "watch",
            "timeframe": "1-10 trading days",
            "confidence_score": 0,
            "reason": "Not included in this cached report.",
        },
        "swing": {
            "rating": "watch",
            "timeframe": "2-8 weeks",
            "confidence_score": 0,
            "reason": "Not included in this cached report.",
        },
        "long_term": {
            "rating": "unknown",
            "timeframe": "6-24 months",
            "confidence_score": 0,
            "reason": "Not included in this cached report.",
        },
    },
    "price_action_structure": {
        "setup_label": "no_clear_setup",
        "structure_label": "insufficient_data",
        "breakout_label": "insufficient_data",
        "pullback_label": "insufficient_data",
        "range_label": "insufficient_data",
        "gap_label": "insufficient_data",
        "labels": ["no_clear_setup"],
        "near_20d_high": False,
        "near_60d_high": False,
        "distance_to_support_pct": None,
        "distance_to_resistance_pct": None,
        "range_compression": False,
        "higher_highs_higher_lows": False,
        "lower_highs_lower_lows": False,
        "gap_up_recent": False,
        "gap_down_recent": False,
        "failed_breakout": False,
        "breakout_attempt": False,
        "pullback_to_sma20": False,
        "pullback_to_sma50": False,
        "support_level": None,
        "resistance_level": None,
        "prior_20d_resistance": None,
        "sma_20": None,
        "sma_50": None,
        "sma_200": None,
    },
    "setup_type": "no_clear_setup",
    "confidence_score": 0,
    "setup_quality_score": 0,
    "entry_timing_score": 0,
    "technical_score": 0,
    "price_structure_score": 0,
    "volume_score": 0,
    "momentum_score": 0,
    "trend_score": 0,
    "fundamental_score": 0,
    "revenue_earnings_quality_score": 0,
    "sentiment_score": 0,
    "news_score": 0,
    "valuation_score": 0,
    "risk_score": 0,
    "risk_reward_score": 0,
    "short_term_score": 0,
    "swing_trade_score": 0,
    "long_term_score": 0,
    "trade_read": "Not included in this cached report.",
    "main_thesis": "Not included in this cached report.",
    "entry_zone": "Not included in this cached report.",
    "confirmation_trigger": "Not included in this cached report.",
    "invalidation_level": "Not included in this cached report.",
    "target_1": "Not included in this cached report.",
    "target_2": "Not included in this cached report.",
    "risk_reward_summary": "Not included in this cached report.",
    "why_it_could_move": "Not included in this cached report.",
    "why_it_could_fail": "Not included in this cached report.",
    "confirmation_signals": ["Generate a fresh report for confirmation signals."],
    "watchlist_action": "Generate a fresh report for actionable levels.",
    "news_summary": "Not included in this cached report.",
    "final_verdict": "neutral wait - generate a fresh report for the updated report contract.",
    "trade_card": None,
}


def _normalize_tier(tier: str | None) -> str:
    return (tier or "free").strip().lower()


def _report_response(report: AIStockReport, cached: bool) -> AIReportResponse:
    created_at = report.created_at or datetime.now(timezone.utc)
    ai_report = {**LEGACY_ACTIONABLE_REPORT_DEFAULTS, **(report.ai_report or {})}
    if "directional_bias" not in ai_report and "swing_bias" in ai_report:
        ai_report["directional_bias"] = ai_report["swing_bias"]
    ai_report = {field: ai_report[field] for field in AIReportOutput.model_fields if field in ai_report}
    return AIReportResponse.model_validate(
        {
            "ticker": report.ticker,
            "created_at": created_at,
            "cached": cached,
            "tier_used": report.tier_used or "unknown",
            "report": ai_report,
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
    user_id = str(current_user.id)
    logger.info(
        "AI report request started ticker=%s user_id=%s tier=%s provider=%s model=%s",
        ticker_symbol,
        user_id,
        tier,
        settings.ai_provider,
        settings.ai_model,
    )

    if tier not in ALLOWED_AI_REPORT_TIERS:
        logger.info("AI report rejected by tier ticker=%s user_id=%s tier=%s", ticker_symbol, user_id, tier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI reports require a pro, trader, or elite account tier.",
        )

    try:
        check_usage_limit(user_id, db)
        logger.info("AI report usage limit passed ticker=%s user_id=%s", ticker_symbol, user_id)

        cached_report = get_fresh_report(user_id, ticker_symbol, db)
        if cached_report:
            logger.info("AI report served from cache ticker=%s user_id=%s report_id=%s", ticker_symbol, user_id, cached_report.id)
            return _report_response(cached_report, cached=True)

        payload = build_ai_payload(ticker_symbol, db)
        payload_log_summary = summarize_ai_payload_for_logs(payload)
        logger.info(
            "AI report payload built ticker=%s user_id=%s payload_summary=%s",
            ticker_symbol,
            user_id,
            payload_log_summary,
        )

        ai_response = generate_single_stock_report(payload, user_id, ticker_symbol, db)
        usage = _pop_usage_metadata(ai_response)
        logger.info(
            "AI report LLM response validated ticker=%s user_id=%s model=%s input_tokens=%s output_tokens=%s",
            ticker_symbol,
            user_id,
            usage["model_used"],
            usage["tokens_input"],
            usage["tokens_output"],
        )

        saved_report = save_report(user_id, ticker_symbol, payload, ai_response, tier, db)
        record_usage_event(
            user_id=user_id,
            ticker=ticker_symbol,
            model_used=str(usage["model_used"]),
            tokens_input=int(usage["tokens_input"]),
            tokens_output=int(usage["tokens_output"]),
            db=db,
        )
        logger.info("AI report saved ticker=%s user_id=%s report_id=%s", ticker_symbol, user_id, saved_report.id)

        return _report_response(saved_report, cached=False)
    except HTTPException as exc:
        logger.warning(
            "AI report request failed ticker=%s user_id=%s status=%s detail=%s",
            ticker_symbol,
            user_id,
            exc.status_code,
            exc.detail,
        )
        raise
    except Exception:
        logger.exception("AI report request crashed ticker=%s user_id=%s", ticker_symbol, user_id)
        raise
