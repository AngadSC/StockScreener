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
    if normalized in {"pro", "trader", "elite"}:
        return settings.ai_monthly_report_limit_pro
    if normalized == "admin":
        return settings.ai_monthly_report_limit_pro
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
) -> None:
    event = AIUsageEvent(
        user_id=_coerce_user_id(user_id),
        ticker=ticker.strip().upper(),
        report_type="single_stock",
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
    )
    db.add(event)
    db.commit()
