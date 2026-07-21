"""Unit tests for the multi-tier billing wiring.

These tests never touch a live Stripe API or a database. They exercise the pure
tier-mapping helpers in ``app.routes.billing`` and the per-tier usage limit in
``app.ai.usage_limits``, mocking ``settings`` via monkeypatch.
"""

from app.ai import usage_limits
from app.routes import billing


def _configure_prices(monkeypatch, pro="price_pro", trader="price_trader", elite="price_elite"):
    monkeypatch.setattr(billing.settings, "STRIPE_PRO_PRICE_ID", pro)
    monkeypatch.setattr(billing.settings, "STRIPE_TRADER_PRICE_ID", trader)
    monkeypatch.setattr(billing.settings, "STRIPE_ELITE_PRICE_ID", elite)


# ---------------------------------------------------------------------------
# _price_to_tier
# ---------------------------------------------------------------------------

def test_price_to_tier_maps_each_configured_price(monkeypatch):
    _configure_prices(monkeypatch)
    assert billing._price_to_tier("price_pro") == "pro"
    assert billing._price_to_tier("price_trader") == "trader"
    assert billing._price_to_tier("price_elite") == "elite"


def test_price_to_tier_unknown_or_empty_returns_none(monkeypatch):
    _configure_prices(monkeypatch)
    assert billing._price_to_tier("price_unknown") is None
    assert billing._price_to_tier(None) is None
    assert billing._price_to_tier("") is None


def test_price_to_tier_ignores_unconfigured_empty_prices(monkeypatch):
    # When no prices are configured, an empty price id must never collide with an
    # unconfigured (empty-string) tier price.
    _configure_prices(monkeypatch, pro="", trader="", elite="")
    assert billing._price_to_tier("") is None
    assert billing._price_to_tier("price_pro") is None


def test_tier_price_id_lookup(monkeypatch):
    _configure_prices(monkeypatch)
    assert billing._tier_price_id("pro") == "price_pro"
    assert billing._tier_price_id("trader") == "price_trader"
    assert billing._tier_price_id("elite") == "price_elite"
    assert billing._tier_price_id("bogus") is None


# ---------------------------------------------------------------------------
# _tier_limit
# ---------------------------------------------------------------------------

def test_tier_limit_per_tier(monkeypatch):
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_pro", 150)
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_trader", 400)
    monkeypatch.setattr(usage_limits.settings, "ai_monthly_report_limit_elite", 1000)

    assert usage_limits._tier_limit("pro") == 150
    assert usage_limits._tier_limit("trader") == 400
    assert usage_limits._tier_limit("elite") == 1000
    # Admin inherits the highest (elite) allowance.
    assert usage_limits._tier_limit("admin") == 1000
    # Case-insensitive and whitespace tolerant.
    assert usage_limits._tier_limit("  Trader ") == 400
    # Free / unknown / missing tiers get no allowance.
    assert usage_limits._tier_limit("free") == 0
    assert usage_limits._tier_limit(None) == 0
    assert usage_limits._tier_limit("mystery") == 0


# ---------------------------------------------------------------------------
# Webhook tier derivation (no live Stripe)
# ---------------------------------------------------------------------------

def _fake_subscription_updated_event(price_id, *, metadata=None):
    """Build a fake customer.subscription.updated event payload."""
    return {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "active",
                "current_period_end": 1893456000,
                "items": {"data": [{"price": {"id": price_id}}]},
                "metadata": metadata or {},
            }
        },
    }


def test_subscription_price_id_extraction():
    event = _fake_subscription_updated_event("price_trader")
    sub = event["data"]["object"]
    assert billing._subscription_price_id(sub) == "price_trader"


def test_subscription_price_id_handles_missing_items():
    assert billing._subscription_price_id({}) is None
    assert billing._subscription_price_id({"items": {"data": []}}) is None


def test_tier_from_subscription_object_uses_price(monkeypatch):
    _configure_prices(monkeypatch)
    sub = _fake_subscription_updated_event("price_elite")["data"]["object"]
    assert billing._tier_from_subscription_object(sub) == "elite"


def test_tier_from_subscription_object_falls_back_to_metadata(monkeypatch):
    _configure_prices(monkeypatch)
    # Unrecognized price, but metadata carries the tier stamped at checkout.
    sub = _fake_subscription_updated_event("price_unknown", metadata={"tier": "trader"})["data"]["object"]
    assert billing._tier_from_subscription_object(sub) == "trader"


def test_tier_from_subscription_object_unresolved_returns_none(monkeypatch):
    _configure_prices(monkeypatch)
    sub = _fake_subscription_updated_event("price_unknown", metadata={})["data"]["object"]
    assert billing._tier_from_subscription_object(sub) is None


def test_portal_plan_change_pro_to_trader(monkeypatch):
    """Simulate a Customer Portal upgrade Pro -> Trader arriving as an updated event."""
    _configure_prices(monkeypatch)
    sub = _fake_subscription_updated_event("price_trader")["data"]["object"]

    tier = billing._tier_from_subscription_object(sub)
    assert tier == "trader"

    class _FakeUser:
        tier = "pro"
        stripe_subscription_id = None
        subscription_status = None
        subscription_current_period_end = None

    user = _FakeUser()
    billing._apply_subscription_state(
        user,
        status_value=sub["status"],
        subscription_id=sub["id"],
        period_end=sub["current_period_end"],
        tier=tier,
    )
    assert user.tier == "trader"
    assert user.stripe_subscription_id == "sub_123"
    assert user.subscription_status == "active"


def test_apply_subscription_state_cancel_downgrades_to_free():
    class _FakeUser:
        tier = "elite"
        stripe_subscription_id = "sub_123"
        subscription_status = "active"
        subscription_current_period_end = None

    user = _FakeUser()
    billing._apply_subscription_state(
        user,
        status_value="canceled",
        subscription_id="sub_123",
        period_end=None,
        tier=None,
    )
    assert user.tier == "free"


def test_apply_subscription_state_active_without_tier_defaults_to_pro():
    class _FakeUser:
        tier = "free"
        stripe_subscription_id = None
        subscription_status = None
        subscription_current_period_end = None

    user = _FakeUser()
    billing._apply_subscription_state(
        user,
        status_value="active",
        subscription_id="sub_123",
        period_end=None,
        tier=None,
    )
    assert user.tier == billing.DEFAULT_TIER == "pro"
