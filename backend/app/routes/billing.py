import json
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import User
from app.services.auth import get_current_active_user

# Routes that require an authenticated user. Mounted under API_V1_PREFIX.
router = APIRouter(prefix="/billing", tags=["billing"])

# Public webhook endpoint. Mounted at root so it sits outside the API rate
# limiter and Stripe can post to a stable URL.
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ACTIVE_STATUSES = {"active", "trialing", "past_due"}

# Paid subscription tiers that map to a Stripe Price.
PAID_TIERS = {"pro", "trader", "elite"}
DEFAULT_TIER = "pro"


def _tier_price_id(tier: str) -> Optional[str]:
    """Map a paid tier to its configured Stripe Price ID (empty string if unset)."""
    return {
        "pro": settings.STRIPE_PRO_PRICE_ID,
        "trader": settings.STRIPE_TRADER_PRICE_ID,
        "elite": settings.STRIPE_ELITE_PRICE_ID,
    }.get(tier)


def _price_to_tier(price_id: Optional[str]) -> Optional[str]:
    """Reverse-map a Stripe Price ID to a tier, ignoring unconfigured (empty) prices."""
    if not price_id:
        return None
    mapping: dict[str, str] = {}
    if settings.STRIPE_PRO_PRICE_ID:
        mapping[settings.STRIPE_PRO_PRICE_ID] = "pro"
    if settings.STRIPE_TRADER_PRICE_ID:
        mapping[settings.STRIPE_TRADER_PRICE_ID] = "trader"
    if settings.STRIPE_ELITE_PRICE_ID:
        mapping[settings.STRIPE_ELITE_PRICE_ID] = "elite"
    return mapping.get(price_id)


def _subscription_price_id(subscription: dict) -> Optional[str]:
    """Extract the first line-item price ID from a Stripe Subscription object."""
    items = subscription.get("items") or {}
    data_list = items.get("data") or []
    if not data_list:
        return None
    price = data_list[0].get("price") or {}
    return price.get("id")


def _tier_from_subscription_object(subscription: dict) -> Optional[str]:
    """Derive a tier from a subscription's price, falling back to its metadata tier."""
    tier = _price_to_tier(_subscription_price_id(subscription))
    if tier:
        return tier
    metadata = subscription.get("metadata") or {}
    meta_tier = str(metadata.get("tier") or "").strip().lower()
    if meta_tier in PAID_TIERS:
        return meta_tier
    return None


def _stripe_client() -> stripe:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this server.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _epoch_to_dt(value: Optional[int]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


async def _read_requested_tier(request: Request) -> str:
    """Parse an optional {"tier": ...} JSON body. Defaults to "pro" (backward compatible)."""
    try:
        raw = await request.body()
    except Exception:
        return DEFAULT_TIER
    if not raw:
        return DEFAULT_TIER
    try:
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return DEFAULT_TIER
    if isinstance(payload, dict) and payload.get("tier"):
        return str(payload["tier"]).strip().lower()
    return DEFAULT_TIER


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the requested subscription tier and return
    its URL. Accepts an optional JSON body {"tier": "pro"|"trader"|"elite"} and
    defaults to "pro" when the body is empty. The frontend redirects the browser to
    the returned URL.
    """
    sdk = _stripe_client()

    tier = await _read_requested_tier(request)
    if tier not in PAID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown subscription tier '{tier}'.",
        )

    price_id = _tier_price_id(tier)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe {tier.capitalize()} price is not configured on this server.",
        )

    session_args = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": settings.STRIPE_SUCCESS_URL,
        "cancel_url": settings.STRIPE_CANCEL_URL,
        "client_reference_id": str(current_user.id),
        "allow_promotion_codes": True,
        "metadata": {"user_id": str(current_user.id), "tier": tier},
        "subscription_data": {"metadata": {"user_id": str(current_user.id), "tier": tier}},
    }

    if current_user.stripe_customer_id:
        session_args["customer"] = current_user.stripe_customer_id
    else:
        session_args["customer_email"] = current_user.email

    try:
        session = sdk.checkout.Session.create(**session_args)
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {exc.user_message or str(exc)}",
        )

    return {"url": session.url, "id": session.id}


@router.post("/create-portal-session")
def create_portal_session(
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a Stripe Customer Portal session so Pro users can manage or cancel
    their subscription, and return its URL for the frontend to redirect to.
    """
    sdk = _stripe_client()

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription",
        )

    print(f"[portal] return_url={settings.STRIPE_PORTAL_RETURN_URL!r} customer={current_user.stripe_customer_id!r}", flush=True)

    try:
        session = sdk.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=settings.STRIPE_PORTAL_RETURN_URL,
        )
    except stripe.error.StripeError as exc:
        print(f"[portal] stripe error: {exc!r}", flush=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {exc.user_message or str(exc)}",
        )

    return {"url": session.url}


def _find_user_for_event(db: Session, *, user_id_meta: Optional[str], customer_id: Optional[str], email: Optional[str] = None) -> Optional[User]:
    if user_id_meta:
        try:
            user = db.query(User).filter(User.id == int(user_id_meta)).first()
        except (TypeError, ValueError):
            user = None
        if user:
            return user
    if customer_id:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            return user
    if email:
        return db.query(User).filter(User.email == email).first()
    return None


def _apply_subscription_state(
    user: User,
    *,
    status_value: Optional[str],
    subscription_id: Optional[str],
    period_end: Optional[int],
    tier: Optional[str],
    customer_id: Optional[str] = None,
) -> None:
    if customer_id:
        user.stripe_customer_id = customer_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    user.subscription_status = status_value
    user.subscription_current_period_end = _epoch_to_dt(period_end)
    if status_value in ACTIVE_STATUSES:
        user.tier = tier or DEFAULT_TIER
    elif status_value in {"canceled", "unpaid", "incomplete_expired"}:
        user.tier = "free"


@webhook_router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        print("[stripe-webhook] STRIPE_WEBHOOK_SECRET is not set — returning 503; all Stripe webhooks will fail until it is configured.", flush=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if data.get("mode") != "subscription":
            return {"received": True}

        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        client_ref = data.get("client_reference_id")
        metadata = data.get("metadata") or {}
        user_id_meta = metadata.get("user_id") or client_ref
        email = (data.get("customer_details") or {}).get("email") or data.get("customer_email")

        user = _find_user_for_event(db, user_id_meta=user_id_meta, customer_id=customer_id, email=email)
        if not user:
            # Nothing we can do — log and acknowledge so Stripe stops retrying.
            print(f"[stripe-webhook] checkout.session.completed had no matching user. session={data.get('id')}")
            return {"received": True, "matched": False}

        # Prefer the tier stamped into checkout metadata; otherwise retrieve the
        # subscription from Stripe and derive the tier from its price. Fall back to
        # the default tier only when nothing resolves.
        tier = str(metadata.get("tier") or "").strip().lower()
        if tier not in PAID_TIERS:
            tier = ""
        if not tier and subscription_id:
            try:
                subscription = _stripe_client().Subscription.retrieve(subscription_id)
                tier = _tier_from_subscription_object(subscription) or ""
            except Exception as exc:  # noqa: BLE001 - never fail the webhook on lookup
                print(f"[stripe-webhook] could not retrieve subscription {subscription_id}: {exc!r}")
        if not tier:
            print(
                f"[stripe-webhook] checkout.session.completed could not resolve tier; "
                f"defaulting to {DEFAULT_TIER}. session={data.get('id')}"
            )
            tier = DEFAULT_TIER

        if customer_id:
            user.stripe_customer_id = customer_id
        if subscription_id:
            user.stripe_subscription_id = subscription_id
        user.subscription_status = "active"
        user.tier = tier
        db.commit()

    elif event_type in {"customer.subscription.updated", "customer.subscription.created"}:
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status_value = data.get("status")
        period_end = data.get("current_period_end")
        if period_end is None:
            items = (data.get("items") or {}).get("data") or []
            if items:
                period_end = items[0].get("current_period_end")
        metadata = data.get("metadata") or {}
        user_id_meta = metadata.get("user_id")

        user = _find_user_for_event(db, user_id_meta=user_id_meta, customer_id=customer_id)
        if not user:
            print(f"[stripe-webhook] {event_type} had no matching user. subscription={subscription_id}")
            return {"received": True, "matched": False}

        # Derive the tier from the subscription's actual price so that plan changes
        # made in the Customer Portal (e.g. Pro -> Trader) land on the right tier.
        tier = _tier_from_subscription_object(data)
        if status_value in ACTIVE_STATUSES and not tier:
            print(
                f"[stripe-webhook] {event_type} could not resolve tier for "
                f"subscription={subscription_id}; defaulting to {DEFAULT_TIER}"
            )
            tier = DEFAULT_TIER

        _apply_subscription_state(
            user,
            status_value=status_value,
            subscription_id=subscription_id,
            period_end=period_end,
            tier=tier,
            customer_id=customer_id,
        )
        db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        metadata = data.get("metadata") or {}
        user_id_meta = metadata.get("user_id")

        user = _find_user_for_event(db, user_id_meta=user_id_meta, customer_id=customer_id)
        if not user:
            return {"received": True, "matched": False}

        user.tier = "free"
        user.subscription_status = "canceled"
        user.stripe_subscription_id = None
        user.subscription_current_period_end = None
        db.commit()

    # All other events are ignored but acknowledged.
    return {"received": True}
