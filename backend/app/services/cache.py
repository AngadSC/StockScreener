import redis
import json
from typing import Optional, Any
from app.config import settings

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True  # Auto-decode bytes to strings
        )
    
    def get(self, key: str) -> Optional[Any]:
        # gets the value from the cache 

        try:
            value = self.redis_client.get(key) 
            if value:
                return json.loads(value)
            return None 
        except Exception as e:
            print(f"Cache get error: {e}")
            return None 
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        try:
            ttl = ttl or settings.STOCK_CACHE_TTL
            serialized = json.dumps(value)
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
    
    def clear_pattern (self, pattern: str) -> bool:
        """Clear all keys matching pattern (e.g., 'stock:*')"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

cache_service = CacheService()