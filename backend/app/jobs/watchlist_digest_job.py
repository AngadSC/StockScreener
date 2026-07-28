"""Scheduled job: send the Elite "Daily Watchlist AI Digest".

Runs each trading-day morning. For every active Elite user it builds a ranked
digest of the AI swing analysis for their watchlist (cache first, then bounded
LLM generation) and emails it.

Hard cost guards (a runaway here spends real LLM + email money):
    - ``EMAIL_ENABLED`` False  -> log and exit BEFORE any LLM call.
    - ``WATCHLIST_DIGEST_ENABLED`` False -> log and exit (unless force).
    - Non-trading day -> exit (unless force).
    - Recipients are pre-filtered on the ``watchlist_digest`` preference, so an
      opted-out user never triggers LLM work nor consumes the per-run cap.
    - Global per-run cap ``DIGEST_MAX_LLM_CALLS_PER_RUN`` -> once exceeded,
      remaining users get digests built from cached reports only.
    - Per-user idempotency via ``already_sent_today`` (unless force).
    - A digest with zero analyzed stocks is never sent (and never logged as
      sent), so a corrective re-run the same day is still possible.

Per-user failures never abort the run.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.ai.watchlist_digest import (
    build_user_digest,
    digest_preheader,
    digest_subject,
    render_digest_html,
)
from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import EmailPreference, User
from app.services.email import already_sent_today, send_categorized_email
from app.utils.market_calendar import is_trading_day

logger = logging.getLogger(__name__)

DIGEST_CATEGORY = "watchlist_digest"
# Tiers eligible to receive the digest. Authoritative for the tier gate on
# PUT /email/preferences (see app/routes/email_prefs.py).
RECIPIENT_TIERS = ("elite",)


def _elite_recipients(db: Session, target_user_id: Optional[int]) -> list[User]:
    """Active Elite users who have NOT opted out of the digest.

    The preference filter is applied here — not after the digest is built —
    because ``build_user_digest`` can spend up to ``ELITE_DIGEST_MAX_STOCKS``
    LLM calls per user. Filtering later would burn budget (and the shared
    per-run cap) on mail that ``send_categorized_email`` then discards as
    "opted_out", starving opted-in users later in the id ordering.

    Users with no ``EmailPreference`` row are included: the model defaults all
    categories to True, and the row is created on first send.
    """
    query = (
        db.query(User)
        .outerjoin(EmailPreference, EmailPreference.user_id == User.id)
        .filter(
            User.is_active.is_(True),
            # Case-insensitive, matching daily_brief_job -- a tier stored as
            # "Elite" must not pass the prefs tier gate yet silently miss here.
            func.lower(User.tier).in_(RECIPIENT_TIERS),
            or_(
                EmailPreference.user_id.is_(None),
                EmailPreference.watchlist_digest.is_(True),
            ),
        )
    )
    if target_user_id is not None:
        query = query.filter(User.id == target_user_id)
    return query.order_by(User.id.asc()).all()


def _new_summary() -> dict[str, Any]:
    return {
        "ran": False,
        "reason": None,
        "date": date.today().isoformat(),
        "users_considered": 0,
        "emails_sent": 0,
        "emails_skipped": 0,
        "emails_failed": 0,
        "empty_watchlists": 0,
        "skipped_no_content": 0,
        "already_sent": 0,
        "llm_calls": 0,
        "cache_hits": 0,
        "ticker_failures": 0,
        "cost_capped_users": 0,
    }


def run_watchlist_digest(
    target_user_id: Optional[int] = None, force: bool = False
) -> dict[str, Any]:
    """Generate and send the watchlist digest to eligible Elite users.

    Args:
        target_user_id: if set, only this user is considered (still must be an
            active Elite user).
        force: bypass the trading-day check, the feature flag, and the
            per-user "already sent today" guard. Does NOT bypass EMAIL_ENABLED
            (the hard cost guard) or the global LLM cap.

    Returns:
        A summary dict (also emitted to the log at the end of the run).
    """
    summary = _new_summary()
    max_stocks = settings.ELITE_DIGEST_MAX_STOCKS
    llm_cap = settings.DIGEST_MAX_LLM_CALLS_PER_RUN

    # --- Hard cost guard: never touch the LLM when we cannot even send. ---
    if not settings.EMAIL_ENABLED:
        summary["reason"] = "email_disabled"
        logger.info("Watchlist digest skipped: EMAIL_ENABLED is False (no LLM calls made).")
        return summary

    if not settings.WATCHLIST_DIGEST_ENABLED and not force:
        summary["reason"] = "feature_disabled"
        logger.info("Watchlist digest skipped: WATCHLIST_DIGEST_ENABLED is False.")
        return summary

    today = date.today()
    if not is_trading_day(today) and not force:
        summary["reason"] = "not_trading_day"
        logger.info("Watchlist digest skipped: %s is not a trading day.", today.isoformat())
        return summary

    summary["ran"] = True
    llm_calls_used = 0
    db = SessionLocal()
    try:
        recipients = _elite_recipients(db, target_user_id)
        summary["users_considered"] = len(recipients)
        logger.info(
            "Watchlist digest run started users=%s force=%s llm_cap=%s max_stocks=%s target_user_id=%s",
            len(recipients),
            force,
            llm_cap,
            max_stocks,
            target_user_id,
        )

        for user in recipients:
            try:
                if not force and already_sent_today(user.id, DIGEST_CATEGORY, db):
                    summary["already_sent"] += 1
                    continue

                remaining_budget = max(llm_cap - llm_calls_used, 0)
                if remaining_budget == 0:
                    summary["cost_capped_users"] += 1
                    logger.info(
                        "Watchlist digest LLM cap reached (%s); user_id=%s served from cache only.",
                        llm_cap,
                        user.id,
                    )

                digest = build_user_digest(
                    user, db, max_stocks=max_stocks, llm_budget=remaining_budget
                )

                if digest is None:
                    summary["empty_watchlists"] += 1
                    continue

                llm_calls_used += digest["llm_calls"]
                summary["llm_calls"] += digest["llm_calls"]
                summary["cache_hits"] += digest["cache_hits"]
                summary["ticker_failures"] += digest["failures"]

                # Every ticker came back "unavailable" (LLM budget exhausted or
                # the provider failed). Sending would mean "We analyzed 0
                # stocks..." AND would write a status=sent log that blocks any
                # corrective re-run today, so skip without logging a send.
                if digest["available_count"] == 0:
                    summary["skipped_no_content"] += 1
                    logger.warning(
                        "Watchlist digest has no analyzed stocks user_id=%s "
                        "attempted=%s failures=%s llm_calls=%s cache_hits=%s; "
                        "skipping send so a re-run today can still deliver.",
                        user.id,
                        digest["analyzed_attempted"],
                        digest["failures"],
                        digest["llm_calls"],
                        digest["cache_hits"],
                    )
                    continue

                result = send_categorized_email(
                    user,
                    DIGEST_CATEGORY,
                    digest_subject(digest),
                    render_digest_html(digest),
                    db,
                    preheader=digest_preheader(digest),
                )
                status = result.get("status")
                if status == "sent":
                    summary["emails_sent"] += 1
                elif status == "skipped":
                    summary["emails_skipped"] += 1
                else:
                    summary["emails_failed"] += 1
                    logger.warning(
                        "Watchlist digest send failed user_id=%s result=%s", user.id, result
                    )
            except Exception:
                summary["emails_failed"] += 1
                logger.exception(
                    "Watchlist digest failed for user_id=%s (run continues)", user.id
                )
                # Roll back any partial state so the next user starts clean.
                try:
                    db.rollback()
                except Exception:
                    pass

        logger.info(
            "Watchlist digest run complete: users=%s sent=%s skipped=%s failed=%s "
            "empty=%s no_content=%s already_sent=%s llm_calls=%s cache_hits=%s "
            "ticker_failures=%s cost_capped_users=%s",
            summary["users_considered"],
            summary["emails_sent"],
            summary["emails_skipped"],
            summary["emails_failed"],
            summary["empty_watchlists"],
            summary["skipped_no_content"],
            summary["already_sent"],
            summary["llm_calls"],
            summary["cache_hits"],
            summary["ticker_failures"],
            summary["cost_capped_users"],
        )
    finally:
        db.close()

    return summary
