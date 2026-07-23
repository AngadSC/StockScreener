"""
Public market data routes: earnings calendar + FRED macro dashboard.

Both endpoints are public (no auth required). /earnings enriches the
response with an `is_watchlisted` flag when a valid auth cookie/header is
present, but tolerates anonymous requests — see get_optional_current_user
below (a local, tolerant variant of app.services.auth.get_current_user).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database.connection import get_db
from app.database.models import EarningsEvent, MacroObservation, Ticker, User, Watchlist
from app.services.cache import cache_service
from app.services.fred import FRED_SERIES

router = APIRouter(prefix="/market", tags=["market"])

MACRO_CACHE_KEY = "market:macro:v1"
MACRO_CACHE_TTL_SECONDS = 3600
SPARKLINE_POINTS = 90


# ============================================
# OPTIONAL AUTH (tolerates anonymous requests)
# ============================================

def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Same token resolution as app.services.auth.get_current_user, but returns
    None instead of raising 401 when there's no/invalid token. Kept local to
    this route file per task scope (auth.py is shared and not to be touched).
    """
    token: Optional[str] = None

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if not token:
        raw_cookie = request.cookies.get(settings.AUTH_COOKIE_NAME)
        if raw_cookie:
            token = raw_cookie[7:].strip() if raw_cookie.lower().startswith("bearer ") else raw_cookie.strip()

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    return db.query(User).filter(User.email == email).first()


# ============================================
# EARNINGS CALENDAR
# ============================================

@router.get("/earnings")
def get_earnings_calendar(
    days: int = Query(14, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Upcoming earnings events for the next `days` days, ordered by date.
    Public endpoint. When authenticated, each event includes is_watchlisted.
    """
    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    events = (
        db.query(EarningsEvent)
        .options(joinedload(EarningsEvent.ticker).joinedload(Ticker.fundamentals))
        .filter(
            EarningsEvent.earnings_date >= today,
            EarningsEvent.earnings_date <= end_date,
        )
        .order_by(EarningsEvent.earnings_date.asc())
        .all()
    )

    watchlisted_ticker_ids: set[int] = set()
    if current_user:
        watchlisted_ticker_ids = {
            ticker_id
            for (ticker_id,) in db.query(Watchlist.ticker_id)
            .filter(Watchlist.user_id == current_user.id)
            .all()
        }

    results = []
    for event in events:
        ticker = event.ticker
        fundamentals = ticker.fundamentals if ticker else None
        results.append({
            "ticker": ticker.symbol if ticker else None,
            "name": ticker.name if ticker else None,
            "market_cap": fundamentals.market_cap if fundamentals else None,
            "earnings_date": event.earnings_date.isoformat(),
            "time_hint": event.time_hint or "unknown",
            "eps_estimate": event.eps_estimate,
            "is_watchlisted": bool(current_user) and event.ticker_id in watchlisted_ticker_ids,
        })

    return {
        "days": days,
        "from_date": today.isoformat(),
        "to_date": end_date.isoformat(),
        "authenticated": current_user is not None,
        "events": results,
    }


# ============================================
# FRED MACRO DASHBOARD
# ============================================

@router.get("/macro")
def get_macro_dashboard(db: Session = Depends(get_db)):
    """
    Macro stat tiles for the frontend dashboard. Redis-cached for 1 hour.
    Returns {configured: false, series: []} when FRED_API_KEY isn't set,
    so the frontend can show a setup notice instead of erroring.
    """
    if not settings.FRED_API_KEY:
        return {"configured": False, "series": []}

    cached = cache_service.get(MACRO_CACHE_KEY)
    if cached is not None:
        return cached

    series_payload = []
    for series_def in FRED_SERIES:
        rows = (
            db.query(MacroObservation)
            .filter(MacroObservation.series_id == series_def["id"])
            .order_by(MacroObservation.date.asc())
            .all()
        )
        if not rows:
            continue

        latest = rows[-1]
        target_prior_date = latest.date - timedelta(days=30)
        prior = next((r for r in reversed(rows) if r.date <= target_prior_date), None)
        change_1m = (latest.value - prior.value) if (prior is not None and latest.value is not None and prior.value is not None) else None

        sparkline = [{"date": r.date.isoformat(), "value": r.value} for r in rows[-SPARKLINE_POINTS:]]

        series_payload.append({
            "id": series_def["id"],
            "label": series_def["label"],
            "unit": series_def["unit"],
            "latest_value": latest.value,
            "latest_date": latest.date.isoformat(),
            "change_1m": change_1m,
            "sparkline": sparkline,
        })

    result = {"configured": True, "series": series_payload}
    cache_service.set(MACRO_CACHE_KEY, result, ttl=MACRO_CACHE_TTL_SECONDS)
    return result
