from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.cache import cache_service
from app.services.market_scans import compute_scans, market_scans_cache_key

# Public, free-tier routes -- no auth required.
router = APIRouter(prefix="/market", tags=["market"])


def _get_or_compute_payload(db: Session) -> dict:
    cache_key = market_scans_cache_key()
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    payload = compute_scans(db)
    # Only cache payloads that actually found data -- an empty/dev DB shouldn't
    # get stuck serving an empty scan for 24h once real data lands.
    if payload.get("as_of_date"):
        cache_service.set(cache_key, payload, ttl=86400)
    return payload


@router.get("/scans")
def get_market_scans(db: Session = Depends(get_db)):
    """
    Full market scanners payload: gainers, losers, 52-week highs/lows, unusual
    volume, gap up/down, and the per-sector performance summary.

    Cached in Redis under `market:scans:<date>` (24h TTL). On a cache miss this
    computes and stores it, so it works immediately in dev without waiting for
    the nightly warm job.
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
