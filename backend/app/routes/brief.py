"""Admin routes for the Daily Market Brief.

Mounted under ``settings.API_V1_PREFIX`` (i.e. ``/api/v1/admin/brief/...``).
Admin-protected via the shared ``get_current_admin_user`` dependency.

    - POST /admin/brief/run     — run the fan-out synchronously (one user or all).
    - GET  /admin/brief/preview — render today's brief HTML for eyeballing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.market_brief import (
    brief_subject,
    build_brief_payload,
    generate_brief,
    render_brief_html,
)
from app.config import settings
from app.database.connection import get_db
from app.database.models import User
from app.jobs.daily_brief_job import run_daily_brief
from app.services import email_templates as tpl
from app.services.auth import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/brief", tags=["admin", "daily-brief"])


class BriefRunRequest(BaseModel):
    user_id: Optional[int] = None
    force: Optional[bool] = False


@router.post("/run")
def trigger_brief_run(
    body: Optional[BriefRunRequest] = None,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Run the daily brief fan-out synchronously and return the summary.

    With ``user_id`` omitted, sends to all eligible Trader/Elite users; with it
    set, only that user. ``force`` re-sends even to users already sent today.
    """
    payload = body or BriefRunRequest()
    return run_daily_brief(target_user_id=payload.user_id, force=bool(payload.force))


@router.get("/preview", response_class=HTMLResponse)
def preview_brief(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render today's brief (generating + caching if needed) for a browser.

    Uses ``force=True`` so the preview renders even while EMAIL_ENABLED is off.
    """
    payload = build_brief_payload(db)
    if payload is None:
        page = tpl.render_notice_page(
            "Daily brief unavailable",
            "Not enough OHLCV history to build a market brief yet.",
        )
        return HTMLResponse(content=page, status_code=200)

    brief = generate_brief(payload, force=True)
    if brief is None:
        page = tpl.render_notice_page(
            "Daily brief unavailable",
            "The market brief could not be generated. Check the AI provider "
            "configuration and server logs.",
        )
        return HTMLResponse(content=page, status_code=200)

    body_html = render_brief_html(payload, brief)
    subject = brief_subject(payload, brief)
    html = tpl.render_base(
        title=subject,
        preheader=brief.get("headline") or subject,
        body_html=body_html,
        unsubscribe_url=(settings.PUBLIC_APP_URL or "").rstrip("/"),
    )
    return HTMLResponse(content=html, status_code=200)
