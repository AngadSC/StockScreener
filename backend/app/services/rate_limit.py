import threading
import time
from typing import Tuple

from app.services.cache import cache_service

_fallback_lock = threading.Lock()
_fallback_counters = {}


def _fallback_rate_limit(key: str, limit: int, window_seconds: int) -> Tuple[bool, int, int]:
    now = int(time.time())
    expires_at = now + window_seconds

    with _fallback_lock:
        existing = _fallback_counters.get(key)
        if existing and existing["expires_at"] > now:
            existing["count"] += 1
            count = existing["count"]
            ttl = existing["expires_at"] - now
        else:
            _fallback_counters[key] = {"count": 1, "expires_at": expires_at}
            count = 1
            ttl = window_seconds

        # Opportunistic cleanup
        stale_keys = [k for k, v in _fallback_counters.items() if v["expires_at"] <= now]
        for stale_key in stale_keys[:100]:
            _fallback_counters.pop(stale_key, None)

    return count <= limit, count, max(ttl, 1)


def check_rate_limit(identifier: str, scope: str, limit: int, window_seconds: int) -> Tuple[bool, int, int]:
    """
    Returns:
        allowed, current_count, ttl_seconds
    """
    now_bucket = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{scope}:{identifier}:{now_bucket}"

    try:
        count = cache_service.redis_client.incr(redis_key)
        if count == 1:
            cache_service.redis_client.expire(redis_key, window_seconds)
        ttl = cache_service.redis_client.ttl(redis_key)
        ttl = ttl if isinstance(ttl, int) and ttl > 0 else window_seconds
        return count <= limit, int(count), int(ttl)
    except Exception:
        return _fallback_rate_limit(redis_key, limit, window_seconds)
