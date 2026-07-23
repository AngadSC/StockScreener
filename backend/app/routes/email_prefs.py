"""Email preference + unsubscribe routes.

Mounted under ``settings.API_V1_PREFIX`` (i.e. ``/api/v1/email/...``), which is
also the base used to build unsubscribe links in outbound email.
"""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.services import email as email_service
from app.services import email_templates as tpl
from app.services.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


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
    """Update any subset of the four category booleans for the current user."""
    prefs = email_service.get_or_create_preferences(current_user.id, db)

    updates = body.model_dump(exclude_unset=True)
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
