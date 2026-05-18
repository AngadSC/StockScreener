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


@router.post("/create-checkout-session")
def create_checkout_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the Pro subscription and return its URL.
    The frontend redirects the browser to the returned URL.
    """
    sdk = _stripe_client()

    if not settings.STRIPE_PRO_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe Pro price is not configured on this server.",
        )

    session_args = {
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRO_PRICE_ID, "quantity": 1}],
        "success_url": settings.STRIPE_SUCCESS_URL,
        "cancel_url": settings.STRIPE_CANCEL_URL,
        "client_reference_id": str(current_user.id),
        "allow_promotion_codes": True,
        "metadata": {"user_id": str(current_user.id)},
        "subscription_data": {"metadata": {"user_id": str(current_user.id)}},
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


def _find_user_for_event(db: Session, *, user_id_meta: Optional[str], customer_id: Optional[str]) -> Optional[User]:
    if user_id_meta:
        try:
            user = db.query(User).filter(User.id == int(user_id_meta)).first()
        except (TypeError, ValueError):
            user = None
        if user:
            return user
    if customer_id:
        return db.query(User).filter(User.stripe_customer_id == customer_id).first()
    return None


def _apply_subscription_state(user: User, *, status_value: Optional[str], subscription_id: Optional[str], period_end: Optional[int]) -> None:
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    user.subscription_status = status_value
    user.subscription_current_period_end = _epoch_to_dt(period_end)
    if status_value in ACTIVE_STATUSES:
        user.tier = "pro"
    elif status_value in {"canceled", "unpaid", "incomplete_expired"}:
        user.tier = "free"


@webhook_router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
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

        user = _find_user_for_event(db, user_id_meta=user_id_meta, customer_id=customer_id)
        if not user:
            # Nothing we can do — log and acknowledge so Stripe stops retrying.
            print(f"[stripe-webhook] checkout.session.completed had no matching user. session={data.get('id')}")
            return {"received": True, "matched": False}

        if customer_id:
            user.stripe_customer_id = customer_id
        if subscription_id:
            user.stripe_subscription_id = subscription_id
        user.subscription_status = "active"
        user.tier = "pro"
        db.commit()

    elif event_type in {"customer.subscription.updated", "customer.subscription.created"}:
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status_value = data.get("status")
        period_end = data.get("current_period_end")
        metadata = data.get("metadata") or {}
        user_id_meta = metadata.get("user_id")

        user = _find_user_for_event(db, user_id_meta=user_id_meta, customer_id=customer_id)
        if not user:
            print(f"[stripe-webhook] {event_type} had no matching user. subscription={subscription_id}")
            return {"received": True, "matched": False}

        _apply_subscription_state(
            user,
            status_value=status_value,
            subscription_id=subscription_id,
            period_end=period_end,
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
