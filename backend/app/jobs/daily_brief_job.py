"""Daily Market Brief fan-out job.

Generates the brief ONCE per trading day (via ``app.ai.market_brief``) and
sends it to every active Trader / Elite subscriber. Per-user failures are
logged and never abort the loop; the run ends with a sent/skipped/failed
summary.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import func

from app.ai.market_brief import (
    brief_subject,
    build_brief_payload,
    generate_brief,
    render_brief_html,
)
from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import User
from app.services import email as email_service
from app.utils.market_calendar import is_trading_day

logger = logging.getLogger(__name__)

# Email category (gated by EmailPreference.daily_brief).
CATEGORY = "daily_brief"
# Tiers eligible to receive the brief.
RECIPIENT_TIERS = ("trader", "elite")


def run_daily_brief(target_user_id: Optional[int] = None, force: bool = False) -> dict[str, Any]:
    """Generate today's brief and fan it out to eligible users.

    Args:
        target_user_id: If set, only this user is considered (admin/testing).
        force: Re-send even to users who already received the brief today.

    Returns:
        A summary dict: ``{status, recipients, sent, skipped, failed}``.
    """
    summary: dict[str, Any] = {
        "status": "ok",
        "recipients": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
    }

    if not settings.DAILY_BRIEF_ENABLED:
        logger.info("Daily brief job disabled (DAILY_BRIEF_ENABLED=False)")
        summary["status"] = "disabled"
        return summary

    db = SessionLocal()
    try:
        payload = build_brief_payload(db)
        if payload is None:
            logger.info("Daily brief: insufficient OHLCV history, skipping")
            summary["status"] = "insufficient_data"
            return summary

        # Weekdays only, and only if the latest OHLCV date is a trading day.
        as_of = date.fromisoformat(payload["as_of_date"])
        if as_of.weekday() >= 5 or not is_trading_day(as_of):
            logger.info("Daily brief: latest OHLCV date %s is not a trading day, skipping", as_of)
            summary["status"] = "not_trading_day"
            return summary

        brief = generate_brief(payload)
        if brief is None:
            # Email disabled (no tokens burned) or the LLM call failed.
            logger.info("Daily brief: no brief available (email disabled or generation failed), skipping send")
            summary["status"] = "no_brief"
            return summary

        subject = brief_subject(payload, brief)
        body_html = render_brief_html(payload, brief)
        preheader = brief.get("headline")

        query = db.query(User).filter(
            User.is_active.is_(True),
            func.lower(User.tier).in_(RECIPIENT_TIERS),
        )
        if target_user_id is not None:
            query = query.filter(User.id == target_user_id)
        recipients = query.all()
        summary["recipients"] = len(recipients)

        for user in recipients:
            try:
                if not force and email_service.already_sent_today(user.id, CATEGORY, db):
                    summary["skipped"] += 1
                    continue

                result = email_service.send_categorized_email(
                    user, CATEGORY, subject, body_html, db, preheader=preheader
                )
                status = result.get("status")
                if status == email_service.STATUS_SENT:
                    summary["sent"] += 1
                elif status == email_service.STATUS_SKIPPED:
                    summary["skipped"] += 1
                else:
                    summary["failed"] += 1
            except Exception:  # never abort the loop on a single user's failure
                logger.exception("Daily brief send failed for user_id=%s", user.id)
                summary["failed"] += 1

        logger.info(
            "Daily brief run complete as_of=%s recipients=%s sent=%s skipped=%s failed=%s",
            payload["as_of_date"],
            summary["recipients"],
            summary["sent"],
            summary["skipped"],
            summary["failed"],
        )
        return summary
    finally:
        db.close()
