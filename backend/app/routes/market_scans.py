from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.cache import cache_service
from app.services.market_scans import (
    MARKET_SCANS_CACHE_TTL,
    compute_scans,
    is_cached_payload_fresh,
    market_scans_cache_key,
)

# Public, free-tier routes -- no auth required.
router = APIRouter(prefix="/market", tags=["market"])


def _get_or_compute_payload(db: Session) -> dict:
    """Serve the cached scans payload, recomputing it when it predates the last sync.

    The cache lives under one stable key; whether it's usable is decided by the
    as_of_date inside it, not by the key or the TTL. That way the 22:30 ET warm
    job's write is still the thing morning traffic reads -- under the old
    date-in-the-key scheme every reader past ET midnight computed a different key
    and missed by construction.
    """
    cache_key = market_scans_cache_key()
    cached = cache_service.get(cache_key)
    if is_cached_payload_fresh(cached):
        return cached

    payload = compute_scans(db)
    # Only cache payloads that actually found data -- an empty/dev DB shouldn't
    # get stuck serving an empty scan once real data lands.
    if payload.get("as_of_date"):
        cache_service.set(cache_key, payload, ttl=MARKET_SCANS_CACHE_TTL)
    return payload


@router.get("/scans")
def get_market_scans(db: Session = Depends(get_db)):
    """
    Full market scanners payload: gainers, losers, 52-week highs/lows, unusual
    volume, gap up/down, and the per-sector performance summary.

    Cached in Redis under `market:scans:latest` (48h TTL, refreshed whenever the
    payload's as_of_date falls behind the last completed trading day). On a miss
    this computes and stores it, so it works immediately in dev without waiting
    for the nightly warm job.
    """
    payload = _get_or_compute_payload(db)
    return payload


@router.get("/sectors")
def get_market_sectors(db: Session = Depends(get_db)):
    """Just the sector heatmap slice of the market scans payload."""
    payload = _get_or_compute_payload(db)
    return {
        "as_of_date": payload.get("as_of_date"),
        "sectors": payload.get("sectors", []),
    }
