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


def _next_month_start() -> datetime:
    """First instant of next month (UTC) — when the monthly allowance resets."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)


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


# The usage-event type that consumes a user's monthly allowance. Background
# features log their generations under a different type (see DIGEST_REPORT_TYPE)
# so they are tracked for cost without being billed to the customer.
BILLABLE_REPORT_TYPE = "single_stock"


def _count_billable_usage(user_pk: int, db: Session) -> int:
    """Billable generations this calendar month.

    Single source of truth for both the enforcement path
    (``check_usage_limit``) and the counter shown in the UI
    (``get_usage_summary``) — if these ever disagreed, the UI would promise
    reports the API then refuses.
    """
    return (
        db.query(AIUsageEvent)
        .filter(
            and_(
                AIUsageEvent.user_id == user_pk,
                AIUsageEvent.created_at >= _month_start(),
                AIUsageEvent.report_type == BILLABLE_REPORT_TYPE,
            )
        )
        .count()
    )


def get_usage_summary(user_id: str, db: Session) -> dict:
    """Where the user stands against their monthly allowance.

    Usage is reported truthfully even for tiers with no allowance (a lapsed
    subscriber sees what they spent before the downgrade), so callers should
    read ``has_access`` rather than inferring it from ``used``.
    """
    user_pk = _coerce_user_id(user_id)
    user = db.query(User).filter(User.id == user_pk).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit = _tier_limit(user.tier)
    used = _count_billable_usage(user_pk, db)
    return {
        "tier": (user.tier or "free").strip().lower(),
        "limit": limit,
        "used": used,
        "remaining": max(limit - used, 0),
        "has_access": limit > 0,
        "period_start": _month_start(),
        "resets_at": _next_month_start(),
    }


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

    usage_count = _count_billable_usage(user_pk, db)
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
    report_type: str = BILLABLE_REPORT_TYPE,
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
