"""Admin routes for the Elite watchlist AI digest.

Kept in its own module (not ``routes/admin.py``) so the digest feature owns its
surface. Reuses the existing ``get_current_admin_user`` dependency for gating.

Endpoints (mounted under ``{API_V1_PREFIX}/admin/digest``):
    - POST /run       {user_id?, force?} -> synchronous run + summary
    - GET  /preview   ?user_id=&generate=  -> rendered HTML for eyeballing
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.watchlist_digest import build_user_digest, render_digest_document
from app.database.connection import get_db
from app.database.models import User
from app.jobs.watchlist_digest_job import run_watchlist_digest
from app.services import email_templates as tpl
from app.services.auth import get_current_admin_user

router = APIRouter(prefix="/admin/digest", tags=["admin", "digest"])
logger = logging.getLogger(__name__)


class DigestRunRequest(BaseModel):
    user_id: Optional[int] = None
    force: bool = False


@router.post("/run")
def trigger_digest_run(
    body: Optional[DigestRunRequest] = None,
    current_user: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Run the digest synchronously and return the run summary.

    Without ``user_id`` this processes every active Elite user (respecting the
    same cost guards as the scheduled run). ``force`` bypasses the trading-day
    check, the feature flag, and the per-user "already sent today" guard, but
    NOT ``EMAIL_ENABLED`` or the global LLM cap.
    """
    payload = body or DigestRunRequest()
    logger.info(
        "Admin digest run requested by user_id=%s target_user_id=%s force=%s",
        current_user.id,
        payload.user_id,
        payload.force,
    )
    summary = run_watchlist_digest(target_user_id=payload.user_id, force=payload.force)
    return {"status": "completed", "summary": summary}


@router.get("/preview", response_class=HTMLResponse)
def preview_digest(
    user_id: int = Query(..., description="User whose watchlist digest to preview"),
    generate: bool = Query(
        False,
        description="Allow LLM generation for cache misses (default: cache-only, no cost)",
    ),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the digest email as a full HTML page for browser inspection.

    Cache-first: by default (``generate=false``) no LLM calls are made — cache
    misses render as "analysis unavailable" lines. Pass ``generate=true`` to let
    the preview build fresh reports on demand.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    llm_budget = None if generate else 0
    digest = build_user_digest(user, db, llm_budget=llm_budget)
    if digest is None:
        return HTMLResponse(
            content=tpl.render_notice_page(
                "Empty watchlist",
                f"User {user_id} has no watchlist tickers to preview.",
            )
        )
    return HTMLResponse(content=render_digest_document(digest))
