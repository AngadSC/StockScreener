"""Tests for the Resend email foundation.

Covers template rendering, preference opt-out short-circuiting (with the HTTP
call mocked), the already_sent_today idempotency helper, and the unsubscribe
token flow. Uses an in-memory SQLite DB (same pattern as the existing AI tests)
so no live Postgres is required.
"""

from __future__ import annotations

import os

# App config requires these; set safe dummies before importing app modules so
# this file runs standalone. create_engine() is lazy, so a dummy URL is fine.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.database.models import EmailPreference, EmailSendLog, User  # noqa: E402
from app.services import email as email_service  # noqa: E402
from app.services import email_templates as tpl  # noqa: E402


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    EmailPreference.__table__.create(engine)
    EmailSendLog.__table__.create(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def user(db: Session) -> User:
    u = User(email="tester@example.com", password_hash="x", tier="pro", is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


class _RecordingResend:
    """Stand-in for email_service._resend_post that records calls."""

    def __init__(self, ok=True, message_id="msg_test_123", error=None):
        self.calls: list[dict] = []
        self.ok = ok
        self.message_id = message_id
        self.error = error

    def __call__(self, payload: dict):
        self.calls.append(payload)
        return self.ok, self.message_id, self.error


@pytest.fixture
def enable_email(monkeypatch):
    """Turn email on with a fake API key for send-path tests."""
    monkeypatch.setattr(email_service.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "re_fake")


# ----------------------------------------------------------------------------
# Template rendering
# ----------------------------------------------------------------------------
def test_render_base_contains_unsubscribe_and_blocks():
    unsubscribe_url = "https://quantorsignal.com/api/v1/email/unsubscribe?token=abc&category=daily_brief"
    body = "".join([
        tpl.heading("Market Brief"),
        tpl.paragraph("Here is your daily summary."),
        tpl.stat_row("S&P 500", "5,400", change_pct=0.85),
        tpl.stat_row("Nasdaq", "17,100", change_pct=-1.10),
        tpl.ticker_card("AAPL", "Apple Inc.", ["Close $182.40", "RSI 61"]),
        tpl.cta_button("View dashboard", "https://quantorsignal.com/dashboard"),
        tpl.divider(),
    ])
    html = tpl.render_base(
        title="Daily Brief",
        preheader="Your market summary",
        body_html=body,
        unsubscribe_url=unsubscribe_url,
    )

    # The URL appears in an href attribute, so '&' is escaped to '&amp;'.
    assert "/api/v1/email/unsubscribe?token=abc&amp;category=daily_brief" in html
    assert "token=abc" in html
    assert "QuantorSignal" in html or "Quantor" in html  # wordmark
    assert "AAPL" in html
    assert "Apple Inc." in html
    assert "View dashboard" in html
    assert "https://quantorsignal.com/dashboard" in html
    assert "Your market summary" in html  # preheader
    assert html.strip().startswith("<!DOCTYPE html>")


def test_stat_row_change_colors():
    up = tpl.stat_row("Up", "10", change_pct=2.0)
    down = tpl.stat_row("Down", "9", change_pct=-2.0)
    assert tpl.POSITIVE in up
    assert tpl.NEGATIVE in down
    # No change arg -> no colored change span
    plain = tpl.stat_row("Flat", "5")
    assert tpl.POSITIVE not in plain and tpl.NEGATIVE not in plain


def test_template_escapes_untrusted_text():
    card = tpl.ticker_card("<script>", "A & B <b>", ["line <x>"])
    assert "<script>" not in card
    assert "&lt;script&gt;" in card
    assert "&amp;" in card


def test_notice_page_is_self_contained():
    page = tpl.render_notice_page("You're unsubscribed", "Done.")
    assert page.strip().startswith("<!DOCTYPE html>")
    assert "You&#x27;re unsubscribed" in page or "unsubscribed" in page
    assert "http://" not in page and "https://" not in page  # no external assets


# ----------------------------------------------------------------------------
# Preferences + unsubscribe URL
# ----------------------------------------------------------------------------
def test_get_or_create_preferences_is_idempotent(db, user):
    p1 = email_service.get_or_create_preferences(user.id, db)
    assert p1.unsubscribe_token
    assert p1.daily_brief is True
    assert p1.watchlist_digest is True
    assert p1.weekly_recap is True
    assert p1.product_updates is True

    p2 = email_service.get_or_create_preferences(user.id, db)
    assert p2.user_id == p1.user_id
    assert p2.unsubscribe_token == p1.unsubscribe_token
    assert db.query(EmailPreference).count() == 1


def test_build_unsubscribe_url():
    url = email_service.build_unsubscribe_url("tok123", "daily_brief")
    assert "/api/v1/email/unsubscribe" in url
    assert "token=tok123" in url
    assert "category=daily_brief" in url


# ----------------------------------------------------------------------------
# Send path
# ----------------------------------------------------------------------------
def test_opt_out_short_circuits_send(db, user, enable_email, monkeypatch):
    prefs = email_service.get_or_create_preferences(user.id, db)
    prefs.daily_brief = False
    db.commit()

    recorder = _RecordingResend()
    monkeypatch.setattr(email_service, "_resend_post", recorder)

    result = email_service.send_categorized_email(
        user, "daily_brief", "Daily Brief", "<p>hi</p>", db
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "opted_out"
    assert recorder.calls == []  # HTTP never invoked

    log = db.query(EmailSendLog).filter_by(category="daily_brief").one()
    assert log.status == "skipped"


def test_send_when_enabled_and_opted_in(db, user, enable_email, monkeypatch):
    recorder = _RecordingResend(ok=True, message_id="msg_abc")
    monkeypatch.setattr(email_service, "_resend_post", recorder)

    result = email_service.send_categorized_email(
        user, "daily_brief", "Daily Brief", tpl.paragraph("Hello"), db
    )

    assert result["status"] == "sent"
    assert result["message_id"] == "msg_abc"
    assert len(recorder.calls) == 1

    payload = recorder.calls[0]
    assert payload["to"] == [user.email]
    assert payload["subject"] == "Daily Brief"
    assert "List-Unsubscribe" in payload["headers"]
    assert "/api/v1/email/unsubscribe" in payload["headers"]["List-Unsubscribe"]
    assert "/api/v1/email/unsubscribe" in payload["html"]  # footer link wrapped in

    log = db.query(EmailSendLog).filter_by(category="daily_brief").one()
    assert log.status == "sent"
    assert log.provider_message_id == "msg_abc"


def test_send_skipped_when_disabled(db, user, monkeypatch):
    monkeypatch.setattr(email_service.settings, "EMAIL_ENABLED", False)
    recorder = _RecordingResend()
    monkeypatch.setattr(email_service, "_resend_post", recorder)

    result = email_service.send_categorized_email(
        user, "product_updates", "Update", "<p>x</p>", db
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "email_disabled"
    assert recorder.calls == []

    log = db.query(EmailSendLog).filter_by(category="product_updates").one()
    assert log.status == "skipped"


def test_send_records_failure(db, user, enable_email, monkeypatch):
    recorder = _RecordingResend(ok=False, message_id=None, error="http_422: bad")
    monkeypatch.setattr(email_service, "_resend_post", recorder)

    result = email_service.send_categorized_email(
        user, "weekly_recap", "Recap", tpl.paragraph("Hi"), db
    )

    assert result["status"] == "failed"
    assert "http_422" in result["error"]
    log = db.query(EmailSendLog).filter_by(category="weekly_recap").one()
    assert log.status == "failed"
    assert "http_422" in log.error


# ----------------------------------------------------------------------------
# Idempotency
# ----------------------------------------------------------------------------
def test_already_sent_today(db, user, enable_email, monkeypatch):
    assert email_service.already_sent_today(user.id, "daily_brief", db) is False

    recorder = _RecordingResend(ok=True, message_id="m1")
    monkeypatch.setattr(email_service, "_resend_post", recorder)
    email_service.send_categorized_email(
        user, "daily_brief", "Daily Brief", tpl.paragraph("Hi"), db
    )

    assert email_service.already_sent_today(user.id, "daily_brief", db) is True
    # A different category is unaffected
    assert email_service.already_sent_today(user.id, "weekly_recap", db) is False


def test_already_sent_today_ignores_skipped(db, user):
    # A skipped log (not a real send) must NOT count as "already sent"
    db.add(EmailSendLog(
        user_id=user.id, category="daily_brief", sent_date=date.today(),
        status="skipped",
    ))
    db.commit()
    assert email_service.already_sent_today(user.id, "daily_brief", db) is False


# ----------------------------------------------------------------------------
# Unsubscribe token flow
# ----------------------------------------------------------------------------
def test_unsubscribe_single_category(db, user):
    prefs = email_service.get_or_create_preferences(user.id, db)
    token = prefs.unsubscribe_token

    ok = email_service.apply_unsubscribe(token, "daily_brief", db)
    assert ok is True

    db.refresh(prefs)
    assert prefs.daily_brief is False
    assert prefs.watchlist_digest is True
    assert prefs.weekly_recap is True
    assert prefs.product_updates is True


def test_unsubscribe_all(db, user):
    prefs = email_service.get_or_create_preferences(user.id, db)
    ok = email_service.apply_unsubscribe(prefs.unsubscribe_token, "all", db)
    assert ok is True

    db.refresh(prefs)
    assert prefs.daily_brief is False
    assert prefs.watchlist_digest is False
    assert prefs.weekly_recap is False
    assert prefs.product_updates is False


def test_unsubscribe_unknown_token_is_safe(db, user):
    # Ensure a real pref exists, then use a bogus token
    email_service.get_or_create_preferences(user.id, db)
    assert email_service.apply_unsubscribe("not-a-real-token", "all", db) is False
    assert email_service.apply_unsubscribe("", "all", db) is False
