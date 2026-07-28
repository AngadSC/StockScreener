"""Email preference + unsubscribe routes.

Mounted under ``settings.API_V1_PREFIX`` (i.e. ``/api/v1/email/...``), which is
also the base used to build unsubscribe links in outbound email.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.jobs.daily_brief_job import RECIPIENT_TIERS as DAILY_BRIEF_TIERS
from app.jobs.watchlist_digest_job import RECIPIENT_TIERS as WATCHLIST_DIGEST_TIERS
from app.services import email as email_service
from app.services import email_templates as tpl
from app.services.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])

# Categories whose sending job only ever fans out to certain tiers. Opting IN to
# one of these on a lower tier used to "save" happily and then silently deliver
# nothing, so the PUT rejects it. Sourced from the jobs themselves so the gate
# can never drift from the recipient queries that actually send the mail.
CATEGORY_REQUIRED_TIERS: dict[str, tuple[str, ...]] = {
    "daily_brief": tuple(t.lower() for t in DAILY_BRIEF_TIERS),
    "watchlist_digest": tuple(t.lower() for t in WATCHLIST_DIGEST_TIERS),
}


def _tier_label(tiers: tuple[str, ...]) -> str:
    """'elite' -> 'Elite'; ('trader', 'elite') -> 'Trader or Elite'."""
    names = [t.capitalize() for t in tiers]
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} or {names[-1]}"


def _assert_tier_allows(category: str, user: User) -> None:
    """Raise 403 if ``user``'s tier can never receive ``category``."""
    required = CATEGORY_REQUIRED_TIERS.get(category)
    if not required:
        return
    if (user.tier or "").strip().lower() in required:
        return

    label = _tier_label(required)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "tier_required",
            "message": (
                f"This email is included with the {label} plan. "
                "Upgrade to turn it on."
            ),
            "category": category,
            "required_tiers": list(required),
            "current_tier": (user.tier or "").strip().lower(),
        },
    )


# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------
class EmailPreferencesResponse(BaseModel):
    daily_brief: bool
    watchlist_digest: bool
    weekly_recap: bool
    product_updates: bool

    model_config = ConfigDict(from_attributes=True)


class EmailPreferencesUpdate(BaseModel):
    """All fields optional — only provided booleans are updated."""
    daily_brief: bool | None = None
    watchlist_digest: bool | None = None
    weekly_recap: bool | None = None
    product_updates: bool | None = None


# ----------------------------------------------------------------------------
# Authenticated preference management
# ----------------------------------------------------------------------------
@router.get("/preferences", response_model=EmailPreferencesResponse)
def get_email_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EmailPreferencesResponse:
    """Return the current user's email preferences (creating defaults if none)."""
    prefs = email_service.get_or_create_preferences(current_user.id, db)
    return EmailPreferencesResponse.model_validate(prefs)


@router.put("/preferences", response_model=EmailPreferencesResponse)
def update_email_preferences(
    body: EmailPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EmailPreferencesResponse:
    """Update any subset of the four category booleans for the current user.

    Turning a category OFF is always allowed. Turning one ON is rejected with
    403 when the user's tier is not on the sending job's recipient list — that
    combination could only ever produce a toggle that says "Saved" and then
    never delivers anything.
    """
    updates = body.model_dump(exclude_unset=True)

    # Validate before touching the row so a rejected request changes nothing.
    for field, value in updates.items():
        if value is True:
            _assert_tier_allows(field, current_user)

    prefs = email_service.get_or_create_preferences(current_user.id, db)
    for field, value in updates.items():
        if value is not None:
            setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)
    return EmailPreferencesResponse.model_validate(prefs)


# ----------------------------------------------------------------------------
# Public one-click unsubscribe (no auth). Accepts GET (browser link) and POST
# (RFC 8058 mailbox one-click). Always returns 200 with a generic message so
# token validity is never leaked.
# ----------------------------------------------------------------------------
@router.api_route(
    "/unsubscribe",
    methods=["GET", "POST"],
    response_class=HTMLResponse,
    include_in_schema=True,
)
def unsubscribe(
    token: str = Query(default=""),
    category: str = Query(default="all"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Turn off a category (or all) for the pref row matching ``token``."""
    try:
        email_service.apply_unsubscribe(token=token, category=category, db=db)
    except Exception:  # never surface internals to a public endpoint
        logger.exception("Unsubscribe handling failed")

    page = tpl.render_notice_page(
        title="You're unsubscribed",
        message=(
            "If this email was subscribed, you've been removed from these "
            "updates. You can re-enable email preferences anytime from your "
            "QuantorSignal account settings."
        ),
    )
    return HTMLResponse(content=page, status_code=200)
