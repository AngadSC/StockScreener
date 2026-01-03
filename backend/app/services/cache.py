import redis
import json
from typing import Optional, Any
from app.config import settings

class CacheService:
    """Redis caching service with optimized TTLs"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl or settings.STOCK_CACHE_TTL
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get remaining TTL (-1 if no expiry, -2 if doesn't exist)"""
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            print(f"Cache TTL error: {e}")
            return -2
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0
    
    def set_with_expiry(self, key: str, value: Any, expire_at: int) -> bool:
        """Set value with Unix timestamp expiry"""
        try:
            serialized = json.dumps(value, default=str)
            return self.redis_client.set(key, serialized, exat=expire_at)
        except Exception as e:
            print(f"Cache set with expiry error: {e}")
            return False

# Singleton instance
cache_service = CacheService()
