"""Resend-based email service for QuantorSignal.

Foundation used by later lifecycle features (daily market brief, watchlist AI
digest, weekly recap). Sends via the Resend HTTP API directly with ``httpx``
(no SDK dependency), honors per-user category preferences, records an audit /
idempotency row per attempt, and never raises to callers.

Public surface:
    - ``get_or_create_preferences(user_id, db)``
    - ``send_categorized_email(user, category, subject, html, db, preheader=)``
    - ``already_sent_today(user_id, category, db)``
    - ``send_test_email(db, user, to_email=, category=)``  (admin diagnostics)
    - ``build_unsubscribe_url(token, category)``
    - ``apply_unsubscribe(token, category, db)``
"""

from __future__ import annotations

import logging
import secrets
from datetime import date
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import EmailPreference, EmailSendLog, User
from app.services import email_templates as tpl

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
_HTTP_TIMEOUT = 15.0

# Map an outbound email category -> the EmailPreference boolean column that
# gates it. Categories not present here are treated as always-on transactional
# mail (still gets an unsubscribe link, but no per-category opt-out column).
CATEGORY_TO_FIELD: dict[str, str] = {
    "daily_brief": "daily_brief",
    "watchlist_digest": "watchlist_digest",
    "weekly_recap": "weekly_recap",
    "product_updates": "product_updates",
}

# Status values recorded in EmailSendLog.status
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


# ----------------------------------------------------------------------------
# Preferences
# ----------------------------------------------------------------------------
def get_or_create_preferences(user_id: int, db: Session) -> EmailPreference:
    """Return the user's EmailPreference row, creating defaults if missing.

    New rows get a random URL-safe unsubscribe token (43 chars, fits in the
    64-char column) and all categories opted-in (model defaults).
    """
    prefs = (
        db.query(EmailPreference)
        .filter(EmailPreference.user_id == user_id)
        .first()
    )
    if prefs is not None:
        return prefs

    prefs = EmailPreference(
        user_id=user_id,
        unsubscribe_token=secrets.token_urlsafe(32),
    )
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs


def apply_unsubscribe(token: str, category: str, db: Session) -> bool:
    """Turn off the given category for the pref row matching ``token``.

    ``category == "all"`` disables every category. Returns True if a matching
    token was found and updated, False otherwise. Callers should return a
    generic response either way (do not leak token validity).
    """
    if not token:
        return False

    prefs = (
        db.query(EmailPreference)
        .filter(EmailPreference.unsubscribe_token == token)
        .first()
    )
    if prefs is None:
        return False

    if category == "all":
        for field in CATEGORY_TO_FIELD.values():
            setattr(prefs, field, False)
    else:
        field = CATEGORY_TO_FIELD.get(category)
        if field is None:
            # Unknown category: opt the user out of everything to be safe.
            for field in CATEGORY_TO_FIELD.values():
                setattr(prefs, field, False)
        else:
            setattr(prefs, field, False)

    db.commit()
    return True


# ----------------------------------------------------------------------------
# Idempotency
# ----------------------------------------------------------------------------
def already_sent_today(user_id: int, category: str, db: Session) -> bool:
    """True if a *successful* send for this user+category already happened today.

    Lets daily jobs be safely re-run without double-sending.
    """
    existing = (
        db.query(EmailSendLog.id)
        .filter(
            EmailSendLog.user_id == user_id,
            EmailSendLog.category == category,
            EmailSendLog.sent_date == date.today(),
            EmailSendLog.status == STATUS_SENT,
        )
        .first()
    )
    return existing is not None


# ----------------------------------------------------------------------------
# URL / HTML helpers
# ----------------------------------------------------------------------------
def build_unsubscribe_url(token: str, category: str) -> str:
    """Build the one-click unsubscribe URL for an email footer / header."""
    base = (settings.PUBLIC_APP_URL or "").rstrip("/")
    return (
        f"{base}{settings.API_V1_PREFIX}/email/unsubscribe"
        f"?token={quote(token, safe='')}&category={quote(category, safe='')}"
    )


def _footer_html(unsubscribe_url: str) -> str:
    """Standalone footer appended to already-complete HTML documents."""
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;"><tr><td align="center" '
        f'style="padding:16px 12px;font-family:{tpl.FONT};font-size:12px;'
        f'color:{tpl.MUTED};">You are receiving this because you have a '
        f'{tpl.BRAND_NAME} account. '
        f'<a href="{tpl._esc_attr(unsubscribe_url)}" target="_blank" '
        f'style="color:{tpl.MUTED};text-decoration:underline;">Unsubscribe</a>.'
        f'</td></tr></table>'
    )


def _compose_html(
    body_or_doc: str,
    subject: str,
    preheader: Optional[str],
    unsubscribe_url: str,
) -> str:
    """Produce the final HTML with exactly one unsubscribe footer.

    If ``body_or_doc`` already looks like a full HTML document, append a footer
    before ``</body>``. Otherwise treat it as body content and wrap it in the
    branded base template (which already includes the footer + link).
    """
    lowered = body_or_doc.lower()
    if "</body>" in lowered or "<html" in lowered:
        footer = _footer_html(unsubscribe_url)
        idx = lowered.rfind("</body>")
        if idx != -1:
            return body_or_doc[:idx] + footer + body_or_doc[idx:]
        return body_or_doc + footer
    return tpl.render_base(
        title=subject,
        preheader=preheader or subject,
        body_html=body_or_doc,
        unsubscribe_url=unsubscribe_url,
    )


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
def _record_log(
    db: Session,
    *,
    user_id: int,
    category: str,
    status: str,
    provider_message_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Persist an EmailSendLog row. Never raises (best-effort audit)."""
    try:
        db.add(
            EmailSendLog(
                user_id=user_id,
                category=category,
                sent_date=date.today(),
                status=status,
                provider_message_id=provider_message_id,
                error=(error[:65535] if error else None),
            )
        )
        db.commit()
    except Exception:  # pragma: no cover - defensive; logging must not break sends
        logger.exception("Failed to write EmailSendLog row")
        try:
            db.rollback()
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Transport
# ----------------------------------------------------------------------------
def _resend_post(payload: dict) -> tuple[bool, Optional[str], Optional[str]]:
    """POST to the Resend API. Returns (ok, provider_message_id, error)."""
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(
            RESEND_ENDPOINT, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
        )
    except Exception as exc:  # network / timeout
        logger.warning("Resend request failed: %s", exc)
        return False, None, f"request_error: {exc}"

    if resp.status_code in (200, 201):
        try:
            message_id = resp.json().get("id")
        except Exception:
            message_id = None
        return True, message_id, None

    error = f"http_{resp.status_code}: {resp.text[:500]}"
    logger.warning("Resend returned %s: %s", resp.status_code, resp.text[:500])
    return False, None, error


def _deliver(
    db: Session,
    *,
    user_id: int,
    to_email: str,
    subject: str,
    html: str,
    category: str,
    unsubscribe_url: str,
    reply_to: Optional[str] = None,
) -> dict:
    """Send one email through Resend and record the outcome. Never raises.

    Honors ``EMAIL_ENABLED`` and a missing API key by short-circuiting to a
    logged "skipped" result. Preference gating is the caller's responsibility.
    """
    if not settings.EMAIL_ENABLED:
        _record_log(db, user_id=user_id, category=category, status=STATUS_SKIPPED,
                    error="email_disabled")
        return {"status": STATUS_SKIPPED, "reason": "email_disabled"}

    if not settings.RESEND_API_KEY:
        _record_log(db, user_id=user_id, category=category, status=STATUS_SKIPPED,
                    error="missing_api_key")
        logger.error("EMAIL_ENABLED is true but RESEND_API_KEY is not set")
        return {"status": STATUS_SKIPPED, "reason": "missing_api_key"}

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
        # RFC 8058 one-click unsubscribe; the /email/unsubscribe route accepts
        # both GET (browser link) and POST (mailbox one-click).
        "headers": {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }
    if reply_to:
        payload["reply_to"] = reply_to

    ok, message_id, error = _resend_post(payload)
    if ok:
        _record_log(db, user_id=user_id, category=category, status=STATUS_SENT,
                    provider_message_id=message_id)
        return {"status": STATUS_SENT, "message_id": message_id}

    _record_log(db, user_id=user_id, category=category, status=STATUS_FAILED,
                error=error)
    return {"status": STATUS_FAILED, "error": error}


# ----------------------------------------------------------------------------
# Public send entry point
# ----------------------------------------------------------------------------
def send_categorized_email(
    user: User,
    category: str,
    subject: str,
    html: str,
    db: Session,
    *,
    preheader: Optional[str] = None,
) -> dict:
    """Send ``html`` to ``user`` for ``category``, honoring their preferences.

    - No-ops with a "skipped" log if EMAIL_ENABLED is False or the user opted
      out of this category.
    - ``html`` may be body content (wrapped in the branded base template) or a
      full HTML document (a footer with the unsubscribe link is appended).
    - Records an EmailSendLog row on every outcome and never raises.

    Returns a status dict, e.g. ``{"status": "sent", "message_id": "..."}``.
    """
    prefs = get_or_create_preferences(user.id, db)

    field = CATEGORY_TO_FIELD.get(category)
    if field is not None and not getattr(prefs, field):
        _record_log(db, user_id=user.id, category=category, status=STATUS_SKIPPED,
                    error="opted_out")
        return {"status": STATUS_SKIPPED, "reason": "opted_out"}

    unsubscribe_url = build_unsubscribe_url(prefs.unsubscribe_token, category)
    final_html = _compose_html(html, subject, preheader, unsubscribe_url)

    return _deliver(
        db,
        user_id=user.id,
        to_email=user.email,
        subject=subject,
        html=final_html,
        category=category,
        unsubscribe_url=unsubscribe_url,
        reply_to=(settings.EMAIL_REPLY_TO or None),
    )


def send_test_email(
    db: Session,
    user: User,
    *,
    to_email: Optional[str] = None,
    category: str = "product_updates",
) -> dict:
    """Admin diagnostic: send a sample base-template email to verify delivery.

    Bypasses per-category preference gating (so an admin who opted out can still
    test) but still respects EMAIL_ENABLED. Sends to ``to_email`` or, by
    default, the admin's own address. Logged under category ``"test"``.
    """
    prefs = get_or_create_preferences(user.id, db)
    recipient = to_email or user.email
    unsubscribe_url = build_unsubscribe_url(prefs.unsubscribe_token, category)

    body = "".join([
        tpl.paragraph(
            "This is a test email from QuantorSignal confirming that outbound "
            "email delivery is configured correctly."
        ),
        tpl.stat_row("Delivery pipeline", "Resend HTTP API"),
        tpl.stat_row("Sample change", "+1.24%", change_pct=1.24),
        tpl.stat_row("Sample change", "-0.87%", change_pct=-0.87),
        tpl.divider(),
        tpl.ticker_card(
            "AAPL", "Apple Inc.",
            ["Close $182.40 (+1.2%)", "Above 50-day average", "RSI 61"],
        ),
        tpl.cta_button("Open QuantorSignal", settings.PUBLIC_APP_URL or "https://quantorsignal.com"),
        tpl.paragraph("If you received this, deliverability is working."),
    ])
    html = tpl.render_base(
        title="QuantorSignal email test",
        preheader="Deliverability check",
        body_html=body,
        unsubscribe_url=unsubscribe_url,
    )

    return _deliver(
        db,
        user_id=user.id,
        to_email=recipient,
        subject="QuantorSignal email delivery test",
        html=html,
        category="test",
        unsubscribe_url=unsubscribe_url,
        reply_to=(settings.EMAIL_REPLY_TO or None),
    )
