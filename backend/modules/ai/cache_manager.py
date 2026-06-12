"""
cache_manager.py - Redis Caching + Response Optimization
T18: Redis caching layer for AI Note Taker

Features:
- Redis support with aioredis
- In-memory LRU fallback when Redis unavailable
- Response compression (gzip) middleware
- Smart cache invalidation
- Provider status caching
- Analytics query caching
"""

import os
import json
import gzip
import hashlib
import logging
import time
from typing import Optional, Any, Dict, List, Callable
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger("cache")

# Try importing Redis
try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("[Cache] redis not available, using in-memory cache")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "300"))  # 5 minutes
CACHE_TTL_PROVIDER_STATUS = int(os.getenv("CACHE_TTL_PROVIDER", "60"))  # 1 minute
CACHE_TTL_ANALYTICS = int(os.getenv("CACHE_TTL_ANALYTICS", "600"))  # 10 minutes


class MemoryCache:
    """Simple in-memory LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._access_time: Dict[str, float] = {}
        self._max_size = max_size

    def _cleanup(self):
        """Remove expired entries"""
        now = time.time()
        expired = [k for k, v in self._ttl.items() if v < now]
        for k in expired:
            self._cache.pop(k, None)
            self._ttl.pop(k, None)
            self._access_time.pop(k, None)

    def _evict_lru(self):
        """Evict least recently used entries if over size limit"""
        if len(self._cache) >= self._max_size:
            sorted_items = sorted(self._access_time.items(), key=lambda x: x[1])
            to_remove = sorted_items[:len(sorted_items) // 10]  # Remove 10%
            for key, _ in to_remove:
                self._cache.pop(key, None)
                self._ttl.pop(key, None)
                self._access_time.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        self._cleanup()
        if key in self._cache:
            if key in self._ttl and self._ttl[key] > time.time():
                self._access_time[key] = time.time()
                return self._cache[key]
            else:
                # Expired
                self.delete(key)
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with optional TTL"""
        self._cleanup()
        self._evict_lru()
        self._cache[key] = value
        self._access_time[key] = time.time()
        if ttl:
            self._ttl[key] = time.time() + ttl

    def delete(self, key: str):
        """Delete key from cache"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._access_time.pop(key, None)

    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        self._ttl.clear()
        self._access_time.clear()

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (simple substring match)"""
        if pattern == "*":
            return list(self._cache.keys())
        return [k for k in self._cache.keys() if pattern in k]


class CacheManager:
    """
    Unified cache manager with Redis primary and in-memory fallback.
    Provides smart caching for expensive operations.
    """

    def __init__(self):
        self._redis: Optional[Any] = None
        self._memory = MemoryCache()
        self._enabled = REDIS_ENABLED and HAS_REDIS
        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection"""
        if self._initialized:
            return

        if self._enabled:
            try:
                self._redis = await aioredis.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                # Test connection
                await self._redis.ping()
                logger.info("[Cache] Redis connected successfully")
                self._initialized = True
            except Exception as e:
                logger.warning("[Cache] Redis connection failed, using memory cache: %s", str(e))
                self._enabled = False
                self._redis = None
        else:
            logger.info("[Cache] Using in-memory cache")

        self._initialized = True

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._initialized = False
            logger.info("[Cache] Redis connection closed")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Create cache key from arguments"""
        key_parts = [prefix]
        for arg in args:
            key_parts.append(str(arg))
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        key = ":".join(key_parts)
        # Hash long keys
        if len(key) > 200:
            key = f"{prefix}:{hashlib.sha256(key.encode()).hexdigest()[:32]}"
        return key

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis or memory)"""
        try:
            if self._redis:
                value = await self._redis.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except:
                        return value

            # Fallback to memory
            return self._memory.get(key)
        except Exception as e:
            logger.error("[Cache] Get error: %s", str(e))
            return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        try:
            ttl = ttl or CACHE_TTL_DEFAULT

            # Always set in memory as backup
            self._memory.set(key, value, ttl)

            if self._redis:
                serialized = json.dumps(value) if not isinstance(value, (str, bytes)) else value
                await self._redis.setex(key, ttl, serialized)
        except Exception as e:
            logger.error("[Cache] Set error: %s", str(e))

    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            self._memory.delete(key)
            if self._redis:
                await self._redis.delete(key)
        except Exception as e:
            logger.error("[Cache] Delete error: %s", str(e))

    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        try:
            # Clear memory
            for key in self._memory.keys(pattern):
                self._memory.delete(key)

            if self._redis:
                # Use scan for production safety
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
        except Exception as e:
            logger.error("[Cache] Clear pattern error: %s", str(e))

    async def get_provider_status(self, provider: str) -> Optional[Dict]:
        """Get cached provider status"""
        key = self._make_key("provider", "status", provider)
        return await self.get(key)

    async def set_provider_status(self, provider: str, status: Dict):
        """Cache provider status"""
        key = self._make_key("provider", "status", provider)
        await self.set(key, status, CACHE_TTL_PROVIDER_STATUS)

    async def get_analytics(self, query_type: str, user_id: str = None) -> Optional[Dict]:
        """Get cached analytics data"""
        key = self._make_key("analytics", query_type, user_id or "global")
        return await self.get(key)

    async def set_analytics(self, query_type: str, data: Dict, user_id: str = None):
        """Cache analytics data"""
        key = self._make_key("analytics", query_type, user_id or "global")
        await self.set(key, data, CACHE_TTL_ANALYTICS)

    async def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            "redis_enabled": self._enabled and self._redis is not None,
            "memory_cache_size": len(self._memory._cache),
        }

        if self._redis:
            try:
                info = await self._redis.info()
                stats["redis_used_memory"] = info.get("used_memory_human", "N/A")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
                stats["redis_uptime"] = info.get("uptime_in_seconds", 0)
            except:
                pass  # nosec B110

        return stats

    def cached(self, prefix: str, ttl: int = None):
        """Decorator to cache function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Create cache key
                key_parts = [prefix, func.__name__]
                for arg in args:
                    if isinstance(arg, (str, int, float, bool)):
                        key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    if isinstance(v, (str, int, float, bool)):
                        key_parts.append(f"{k}:{v}")
                cache_key = ":".join(key_parts)

                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Call function
                result = await func(*args, **kwargs)

                # Cache result
                if result is not None:
                    await self.set(cache_key, result, ttl)

                return result
            return wrapper
        return decorator


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def get_cache(key: str) -> Optional[Any]:
    """Get value from global cache"""
    return await cache_manager.get(key)


async def set_cache(key: str, value: Any, ttl: int = None):
    """Set value in global cache"""
    await cache_manager.set(key, value, ttl)


async def delete_cache(key: str):
    """Delete key from global cache"""
    await cache_manager.delete(key)


async def clear_cache_pattern(pattern: str):
    """Clear keys matching pattern"""
    await cache_manager.clear_pattern(pattern)


def cached(prefix: str, ttl: int = None):
    """Decorator for caching function results"""
    return cache_manager.cached(prefix, ttl)


# Response Compression Middleware
class CompressionMiddleware:
    """Gzip compression middleware for FastAPI"""

    def __init__(self, minimum_size: int = 1000):
        self.minimum_size = minimum_size

    async def __call__(self, request, call_next):
        response = await call_next(request)

        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response

        # Check response type and size
        if response.status_code != 200:
            return response

        body = getattr(response, 'body', None)
        if body and len(body) >= self.minimum_size:
            compressed = gzip.compress(body)
            if len(compressed) < len(body):
                response.body = compressed
                response.headers["content-encoding"] = "gzip"
                response.headers["content-length"] = str(len(compressed))

        return response


# Initialize on module load
async def init_cache():
    """Initialize cache manager"""
    await cache_manager.initialize()


async def close_cache():
    """Close cache manager"""
    await cache_manager.close()


__all__ = [
    "cache_manager",
    "CacheManager",
    "MemoryCache",
    "CompressionMiddleware",
    "get_cache",
    "set_cache",
    "delete_cache",
    "clear_cache_pattern",
    "cached",
    "init_cache",
    "close_cache",
    "HAS_REDIS",
    "REDIS_ENABLED",
]
