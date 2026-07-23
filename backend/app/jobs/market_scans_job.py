"""
Nightly job: pre-warm the Redis cache for the free market-scanners feature
(gainers/losers, 52-week highs/lows, unusual volume, gaps, sector heatmap).

Registered in app.jobs.stock_loader (the live scheduler) to run at 22:30 ET,
30 minutes after the 21:00 ET daily_ohlcv sync finishes, so the cache is warm
before the first visitor hits /market/scans in the morning. The route itself
also computes-and-caches on a miss, so this job is a performance optimization,
not a correctness dependency -- the feature works even if this job never ran.
"""
from app.database.connection import SessionLocal
from app.services.cache import cache_service
from app.services.market_scans import compute_scans, market_scans_cache_key


def warm_market_scans_cache():
    """Compute today's market scans payload and store it in Redis (TTL 24h)."""
    db = SessionLocal()
    try:
        print("\n⏰ Warming market scans cache...")
        payload = compute_scans(db)
        cache_key = market_scans_cache_key()
        cache_service.set(cache_key, payload, ttl=86400)
        print(f"   ✓ Cached {cache_key} (as_of_date={payload.get('as_of_date')})")
    except Exception as e:
        print(f"   ✗ Error warming market scans cache: {e}")
    finally:
        db.close()
