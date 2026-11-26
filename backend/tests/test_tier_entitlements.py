"""Entitlement tests for the paid tiers (Pro / Trader / Elite).

Where ``test_billing_tiers.py`` covers the pure Stripe/tier mapping helpers,
this module asserts that every benefit advertised on the pricing page is
actually enforced against real database rows:

    Pro     - AI Swing Analyzer, 150 reports/month
    Trader  - everything in Pro, 400 reports/month, Daily Market Brief email
    Elite   - everything in Trader, 1,000 reports/month, Daily Watchlist Digest

It also pins the advertised numbers on the marketing page to the server-side
limits, so a copy edit on the pricing page can never silently promise an
allowance the backend does not grant.

In-memory SQLite; no network, no Stripe, no LLM, no Redis.
"""

from __future__ import annotations

import os

# App config requires these; set safe dummies before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import re  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.ai import usage_limits  # noqa: E402
from app.database.models import (  # noqa: E402
    AIUsageEvent,
    EmailPreference,
    EmailSendLog,
    User,
)
from app.jobs import daily_brief_job as brief_job  # noqa: E402
from app.jobs import watchlist_digest_job as digest_job  # noqa: E402
from app.routes import ai_reports, billing, email_prefs  # noqa: E402

# The allowances advertised on the pricing page, per tier.
ADVERTISED_LIMITS = {"pro": 150, "trader": 400, "elite": 1000}


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def db() -> Session:
    # StaticPool + check_same_thread keeps the one in-memory DB reachable from
    # the TestClient's worker thread as well as the test's own thread.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, AIUsageEvent, EmailPreference, EmailSendLog):
        model.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _pin_limits(monkeypatch):
    """Pin the per-tier allowances so an env override can't skew assertions."""
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_pro", 150)
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_trader", 400)
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_elite", 1000)


def _make_user(db: Session, *, tier: str, is_active: bool = True) -> User:
    user = User(
        email=f"{tier}-{db.query(User).count()}@example.com",
        password_hash="x",
        tier=tier,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_usage(
    db: Session,
    user: User,
    count: int,
    *,
    report_type: str = "single_stock",
    created_at: datetime | None = None,
) -> None:
    stamp = created_at or datetime.now(timezone.utc)
    for _ in range(count):
        db.add(
            AIUsageEvent(
                user_id=user.id,
                ticker="AAPL",
                report_type=report_type,
                model_used="test-model",
                tokens_input=1,
                tokens_output=1,
                created_at=stamp,
            )
        )
    db.commit()


# ----------------------------------------------------------------------------
# AI report access - who may generate a report at all
# ----------------------------------------------------------------------------
def test_paid_tiers_may_generate_reports_free_may_not():
    """The route's tier gate matches the tiers that map to a Stripe price."""
    assert ai_reports.ALLOWED_AI_REPORT_TIERS == billing.PAID_TIERS
    assert "free" not in ai_reports.ALLOWED_AI_REPORT_TIERS


def test_free_tier_has_no_report_allowance(db):
    user = _make_user(db, tier="free")
    with pytest.raises(HTTPException) as exc:
        usage_limits.check_usage_limit(str(user.id), db)
    assert exc.value.status_code == 429
    assert "not available for this account tier" in exc.value.detail


@pytest.mark.parametrize("tier,limit", sorted(ADVERTISED_LIMITS.items()))
def test_tier_allows_exactly_the_advertised_number_of_reports(db, tier, limit):
    """One report below the cap passes; the cap itself is the hard stop."""
    user = _make_user(db, tier=tier)

    _add_usage(db, user, limit - 1)
    usage_limits.check_usage_limit(str(user.id), db)  # must not raise

    _add_usage(db, user, 1)
    with pytest.raises(HTTPException) as exc:
        usage_limits.check_usage_limit(str(user.id), db)
    assert exc.value.status_code == 429
    assert str(limit) in exc.value.detail


def test_upgrading_tier_immediately_restores_access(db):
    """A Pro user at their cap can generate again the moment they hit Trader."""
    user = _make_user(db, tier="pro")
    _add_usage(db, user, ADVERTISED_LIMITS["pro"])
    with pytest.raises(HTTPException):
        usage_limits.check_usage_limit(str(user.id), db)

    user.tier = "trader"
    db.commit()
    usage_limits.check_usage_limit(str(user.id), db)  # must not raise


def test_digest_generations_do_not_consume_the_monthly_quota(db):
    """Elite's automated digest is a benefit, not a charge against the 1,000."""
    user = _make_user(db, tier="elite")
    _add_usage(db, user, 1200, report_type=usage_limits.DIGEST_REPORT_TYPE)
    usage_limits.check_usage_limit(str(user.id), db)  # must not raise


def test_quota_resets_at_the_start_of_the_month(db):
    user = _make_user(db, tier="pro")
    now = datetime.now(timezone.utc)
    last_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(days=1)
    _add_usage(db, user, ADVERTISED_LIMITS["pro"], created_at=last_month)
    usage_limits.check_usage_limit(str(user.id), db)  # last month's usage is spent


def test_another_users_usage_is_not_counted(db):
    heavy = _make_user(db, tier="pro")
    light = _make_user(db, tier="pro")
    _add_usage(db, heavy, ADVERTISED_LIMITS["pro"])
    usage_limits.check_usage_limit(str(light.id), db)  # must not raise


def test_record_usage_event_counts_toward_the_limit(db):
    """The write path and the read path agree on what counts."""
    user = _make_user(db, tier="pro")
    _add_usage(db, user, ADVERTISED_LIMITS["pro"] - 1)
    usage_limits.record_usage_event(str(user.id), "msft", "test-model", 10, 20, db)
    with pytest.raises(HTTPException):
        usage_limits.check_usage_limit(str(user.id), db)


def test_record_digest_usage_event_is_logged_but_not_charged(db):
    """Digest events are still written (cost tracking) under their own type."""
    user = _make_user(db, tier="elite")
    usage_limits.record_digest_usage_event(str(user.id), "nvda", "test-model", 10, 20, db)
    events = db.query(AIUsageEvent).all()
    assert len(events) == 1
    assert events[0].report_type == usage_limits.DIGEST_REPORT_TYPE


# ----------------------------------------------------------------------------
# Email entitlements - Daily Market Brief (Trader+) / Watchlist Digest (Elite)
# ----------------------------------------------------------------------------
def _put_prefs(user: User, db: Session, **fields):
    body = email_prefs.EmailPreferencesUpdate(**fields)
    return email_prefs.update_email_preferences(body, user, db)


@pytest.mark.parametrize("tier", ["free", "pro"])
def test_daily_brief_toggle_rejected_below_trader(db, tier):
    user = _make_user(db, tier=tier)
    with pytest.raises(HTTPException) as exc:
        _put_prefs(user, db, daily_brief=True)
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "tier_required"
    assert exc.value.detail["required_tiers"] == ["trader", "elite"]


@pytest.mark.parametrize("tier", ["trader", "elite"])
def test_daily_brief_toggle_allowed_for_trader_and_elite(db, tier):
    user = _make_user(db, tier=tier)
    assert _put_prefs(user, db, daily_brief=True).daily_brief is True


@pytest.mark.parametrize("tier", ["free", "pro", "trader"])
def test_watchlist_digest_toggle_rejected_below_elite(db, tier):
    user = _make_user(db, tier=tier)
    with pytest.raises(HTTPException) as exc:
        _put_prefs(user, db, watchlist_digest=True)
    assert exc.value.status_code == 403
    assert exc.value.detail["required_tiers"] == ["elite"]


def test_watchlist_digest_toggle_allowed_for_elite(db):
    user = _make_user(db, tier="elite")
    assert _put_prefs(user, db, watchlist_digest=True).watchlist_digest is True


def test_opting_out_is_always_allowed(db):
    """Downgraded users must still be able to turn a gated email off."""
    user = _make_user(db, tier="free")
    prefs = _put_prefs(user, db, daily_brief=False, watchlist_digest=False)
    assert prefs.daily_brief is False
    assert prefs.watchlist_digest is False


def test_rejected_toggle_persists_nothing(db):
    """A 403 on one field must not half-apply the rest of the payload."""
    user = _make_user(db, tier="pro")
    with pytest.raises(HTTPException):
        _put_prefs(user, db, daily_brief=True, product_updates=False)
    prefs = db.query(EmailPreference).filter(EmailPreference.user_id == user.id).first()
    assert prefs is None or prefs.product_updates is True


def test_ungated_categories_work_on_every_tier(db):
    user = _make_user(db, tier="free")
    assert _put_prefs(user, db, product_updates=True).product_updates is True


# ----------------------------------------------------------------------------
# Daily Market Brief fan-out - the Trader-and-up recipient list
# ----------------------------------------------------------------------------
@pytest.fixture
def brief_run(db, monkeypatch):
    """Run the brief job against the test DB with the LLM/email layers faked."""
    sent: list[User] = []

    monkeypatch.setattr(brief_job.settings, "DAILY_BRIEF_ENABLED", True)
    monkeypatch.setattr(brief_job, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(
        brief_job, "build_brief_payload", lambda _db: {"as_of_date": "2026-01-05"}
    )
    monkeypatch.setattr(brief_job, "is_trading_day", lambda _d: True)
    monkeypatch.setattr(brief_job, "generate_brief", lambda _p: {"headline": "h"})
    monkeypatch.setattr(brief_job, "brief_subject", lambda _p, _b: "Subject")
    monkeypatch.setattr(brief_job, "render_brief_html", lambda _p, _b: "<p>brief</p>")
    monkeypatch.setattr(
        brief_job.email_service, "already_sent_today", lambda *_a, **_k: False
    )
    monkeypatch.setattr(
        brief_job.email_service,
        "send_categorized_email",
        lambda user, *_a, **_k: sent.append(user) or {"status": "sent"},
    )

    def _run():
        summary = brief_job.run_daily_brief()
        return summary, [u.email for u in sent]

    return _run


def test_brief_goes_to_trader_and_elite_only(db, brief_run):
    trader = _make_user(db, tier="trader")
    elite = _make_user(db, tier="elite")
    _make_user(db, tier="pro")
    _make_user(db, tier="free")

    summary, recipients = brief_run()

    assert summary["status"] == "ok"
    assert summary["sent"] == 2
    assert sorted(recipients) == sorted([trader.email, elite.email])


def test_brief_skips_deactivated_accounts(db, brief_run):
    _make_user(db, tier="elite", is_active=False)
    summary, recipients = brief_run()
    assert summary["recipients"] == 0
    assert recipients == []


def test_brief_matches_tier_case_insensitively(db, brief_run):
    """A tier written as "Elite" by any code path still gets the brief."""
    _make_user(db, tier="Elite")
    summary, _recipients = brief_run()
    assert summary["sent"] == 1


def test_brief_disabled_flag_sends_nothing(db, brief_run, monkeypatch):
    _make_user(db, tier="elite")
    monkeypatch.setattr(brief_job.settings, "DAILY_BRIEF_ENABLED", False)
    summary, recipients = brief_run()
    assert summary["status"] == "disabled"
    assert recipients == []


# ----------------------------------------------------------------------------
# Advertised copy vs. enforced entitlements
# ----------------------------------------------------------------------------
PRICING_PAGE = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "app"
    / "pricing"
    / "page.tsx"
)


def _pricing_source() -> str:
    if not PRICING_PAGE.exists():
        pytest.skip(f"pricing page not found at {PRICING_PAGE}")
    return PRICING_PAGE.read_text(encoding="utf-8")


@pytest.mark.parametrize("tier,limit", sorted(ADVERTISED_LIMITS.items()))
def test_pricing_page_advertises_the_enforced_limit(tier, limit):
    """The page says "N AI reports monthly"; the server must grant exactly N."""
    source = _pricing_source()
    advertised = {
        int(m.replace(",", ""))
        for m in re.findall(r"([\d,]+) AI reports monthly", source)
    }
    assert limit in advertised, (
        f"pricing page does not advertise {limit} AI reports for {tier}; "
        f"found {sorted(advertised)}"
    )


def test_pricing_page_lists_every_paid_tier():
    source = _pricing_source()
    for tier in billing.PAID_TIERS:
        assert f"tier: '{tier}'" in source, f"pricing page has no {tier} plan card"


def test_email_gate_tiers_match_the_sending_jobs():
    """The 403 gate is sourced from the jobs - assert they stayed in sync."""
    assert email_prefs.CATEGORY_REQUIRED_TIERS["daily_brief"] == brief_job.RECIPIENT_TIERS
    assert (
        email_prefs.CATEGORY_REQUIRED_TIERS["watchlist_digest"]
        == digest_job.RECIPIENT_TIERS
    )


def test_config_defaults_match_the_advertised_limits():
    """Guards the shipped defaults, independent of the monkeypatched fixture."""
    from app.config import Settings

    fields = Settings.model_fields
    assert fields["ai_monthly_report_limit_pro"].default == ADVERTISED_LIMITS["pro"]
    assert fields["ai_monthly_report_limit_trader"].default == ADVERTISED_LIMITS["trader"]
    assert fields["ai_monthly_report_limit_elite"].default == ADVERTISED_LIMITS["elite"]


# ----------------------------------------------------------------------------
# Usage counter - what the UI shows must match what the API enforces
# ----------------------------------------------------------------------------
def test_usage_summary_reports_the_tier_allowance(db):
    user = _make_user(db, tier="trader")
    _add_usage(db, user, 25)

    summary = usage_limits.get_usage_summary(str(user.id), db)

    assert summary["tier"] == "trader"
    assert summary["limit"] == ADVERTISED_LIMITS["trader"]
    assert summary["used"] == 25
    assert summary["remaining"] == ADVERTISED_LIMITS["trader"] - 25
    assert summary["has_access"] is True


def test_usage_summary_for_free_tier_has_no_allowance(db):
    user = _make_user(db, tier="free")
    summary = usage_limits.get_usage_summary(str(user.id), db)
    assert summary["limit"] == 0
    assert summary["remaining"] == 0
    assert summary["has_access"] is False


def test_usage_summary_excludes_digest_generations(db):
    """The counter must not show the customer usage they were never charged."""
    user = _make_user(db, tier="elite")
    _add_usage(db, user, 3)
    _add_usage(db, user, 40, report_type=usage_limits.DIGEST_REPORT_TYPE)

    summary = usage_limits.get_usage_summary(str(user.id), db)
    assert summary["used"] == 3


def test_usage_summary_counts_only_the_current_month(db):
    user = _make_user(db, tier="pro")
    now = datetime.now(timezone.utc)
    last_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(days=1)
    _add_usage(db, user, 30, created_at=last_month)
    _add_usage(db, user, 4)

    summary = usage_limits.get_usage_summary(str(user.id), db)
    assert summary["used"] == 4
    assert summary["remaining"] == ADVERTISED_LIMITS["pro"] - 4


def test_usage_summary_remaining_never_goes_negative(db):
    """A downgrade can leave usage above the new cap; the meter must floor at 0."""
    user = _make_user(db, tier="elite")
    _add_usage(db, user, 500)
    user.tier = "pro"  # downgraded mid-month, 500 already spent vs a 150 cap
    db.commit()

    summary = usage_limits.get_usage_summary(str(user.id), db)
    assert summary["used"] == 500
    assert summary["remaining"] == 0
    assert summary["has_access"] is True  # Pro still has a plan, just no headroom


def test_usage_summary_resets_at_start_of_next_month(db):
    user = _make_user(db, tier="pro")
    summary = usage_limits.get_usage_summary(str(user.id), db)

    period_start = summary["period_start"]
    resets_at = summary["resets_at"]
    assert period_start.day == 1 and resets_at.day == 1
    assert resets_at > period_start
    # Exactly one month apart, December rollover included.
    assert (resets_at.year, resets_at.month) == (
        (period_start.year + 1, 1)
        if period_start.month == 12
        else (period_start.year, period_start.month + 1)
    )


@pytest.mark.parametrize("tier,limit", sorted(ADVERTISED_LIMITS.items()))
def test_counter_and_enforcement_never_disagree(db, tier, limit):
    """"1 report left" must mean the next request succeeds; "0 left" that it fails."""
    user = _make_user(db, tier=tier)
    _add_usage(db, user, limit - 1)

    assert usage_limits.get_usage_summary(str(user.id), db)["remaining"] == 1
    usage_limits.check_usage_limit(str(user.id), db)  # the promised report

    _add_usage(db, user, 1)
    assert usage_limits.get_usage_summary(str(user.id), db)["remaining"] == 0
    with pytest.raises(HTTPException):
        usage_limits.check_usage_limit(str(user.id), db)


def test_usage_summary_rejects_unknown_user(db):
    with pytest.raises(HTTPException) as exc:
        usage_limits.get_usage_summary("9999", db)
    assert exc.value.status_code == 404


def test_usage_summary_serializes_to_the_api_schema(db):
    """The route's response_model must accept the summary dict unchanged."""
    from app.ai.schemas import AIUsageSummary

    user = _make_user(db, tier="elite")
    _add_usage(db, user, 7)
    payload = AIUsageSummary(**usage_limits.get_usage_summary(str(user.id), db))

    assert payload.tier == "elite"
    assert payload.used == 7
    assert payload.remaining == ADVERTISED_LIMITS["elite"] - 7
    assert payload.has_access is True


# ----------------------------------------------------------------------------
# GET /api/ai-reports/usage - the HTTP surface the meter calls
# ----------------------------------------------------------------------------
def _usage_client(db: Session, user: User | None):
    """Minimal app mounting only the AI router, with auth/db dependencies faked.

    Deliberately avoids importing ``app.main`` so the test never boots the
    scheduler, Redis or a real database connection.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.database.connection import get_db
    from app.services.auth import get_current_user

    test_app = FastAPI()
    test_app.include_router(ai_reports.router)
    test_app.dependency_overrides[get_db] = lambda: db
    if user is not None:
        test_app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(test_app)


def test_usage_endpoint_returns_the_meter_payload(db):
    user = _make_user(db, tier="trader")
    _add_usage(db, user, 12)

    response = _usage_client(db, user).get("/api/ai-reports/usage")

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "trader"
    assert body["limit"] == ADVERTISED_LIMITS["trader"]
    assert body["used"] == 12
    assert body["remaining"] == ADVERTISED_LIMITS["trader"] - 12
    assert body["has_access"] is True
    assert body["resets_at"].startswith(str(datetime.now(timezone.utc).year))


def test_usage_endpoint_requires_authentication(db):
    """No override for get_current_user - the real dependency must reject."""
    response = _usage_client(db, None).get("/api/ai-reports/usage")
    assert response.status_code in (401, 403)


def test_usage_endpoint_is_not_shadowed_by_the_ticker_route(db):
    """"usage" must resolve to the counter, never be treated as a ticker."""
    user = _make_user(db, tier="pro")
    client = _usage_client(db, user)

    assert client.get("/api/ai-reports/usage").status_code == 200
    # The generation route is POST-only, so the GET path is unambiguous.
    assert client.get("/api/ai-reports/AAPL").status_code == 405
