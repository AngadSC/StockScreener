from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import AIUsageEvent, User


def _coerce_user_id(user_id: str) -> int:
    try:
        return int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _tier_limit(tier: str | None) -> int:
    normalized = (tier or "free").strip().lower()
    if normalized == "pro":
        return settings.ai_monthly_report_limit_pro
    if normalized == "trader":
        return settings.ai_monthly_report_limit_trader
    if normalized == "elite":
        return settings.ai_monthly_report_limit_elite
    if normalized == "admin":
        # Admins get the highest configured allowance.
        return settings.ai_monthly_report_limit_elite
    return 0


def check_usage_limit(user_id: str, db: Session) -> None:
    user_pk = _coerce_user_id(user_id)
    user = db.query(User).filter(User.id == user_pk).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit = _tier_limit(user.tier)
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI reports are not available for this account tier.",
        )

    usage_count = (
        db.query(AIUsageEvent)
        .filter(
            and_(
                AIUsageEvent.user_id == user_pk,
                AIUsageEvent.created_at >= _month_start(),
                AIUsageEvent.report_type == "single_stock",
            )
        )
        .count()
    )
    if usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly AI report limit reached ({limit}).",
        )


def record_usage_event(
    user_id: str,
    ticker: str,
    model_used: str,
    tokens_input: int,
    tokens_output: int,
    db: Session,
    report_type: str = "single_stock",
) -> None:
    """Record a single AI generation as a usage event.

    ``report_type`` defaults to ``"single_stock"`` so existing callers keep
    their behavior (these are the events counted by ``check_usage_limit``).
    Background features that must NOT consume a user's on-demand quota — such
    as the Elite watchlist digest — pass a different ``report_type`` (e.g.
    ``"watchlist_digest"``) so the event is logged for cost tracking but not
    counted against the monthly limit.
    """
    event = AIUsageEvent(
        user_id=_coerce_user_id(user_id),
        ticker=ticker.strip().upper(),
        report_type=report_type,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
    )
    db.add(event)
    db.commit()


# Usage event type for digest-generated reports. Intentionally distinct from
# "single_stock" so check_usage_limit (which counts only "single_stock") never
# charges a user's on-demand quota for the automated morning digest.
DIGEST_REPORT_TYPE = "watchlist_digest"


def record_digest_usage_event(
    user_id: str,
    ticker: str,
    model_used: str,
    tokens_input: int,
    tokens_output: int,
    db: Session,
) -> None:
    """Record an LLM generation performed for the Elite watchlist digest.

    Thin wrapper over ``record_usage_event`` that stamps
    ``report_type="watchlist_digest"`` so digest generations are tracked for
    cost/analytics without consuming the user's on-demand monthly allowance.
    """
    record_usage_event(
        user_id=user_id,
        ticker=ticker,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        db=db,
        report_type=DIGEST_REPORT_TYPE,
    )
