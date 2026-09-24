"""
Tests for backend/modules/ai/cache_manager.py — Redis cache layer with
in-memory LRU fallback.

Cache is the linchpin of the hot path: every analytics query, every
provider status check, and every expensive AI call goes through it. If
the in-memory fallback gets the TTL/LRU semantics wrong, the backend
either serves stale data (TTL bug) or memory-grows unbounded (LRU bug).

We test the in-memory LRU path (no Redis is installed in CI) and the
key-generation helper. The Redis path is exercised in environments with
REDIS_URL set, but the contract is the same — MemoryCache and Redis are
interchangeable behind the async wrapper.
"""

import asyncio
import os
import sys
import time

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

# Force in-memory mode (no Redis)
os.environ["REDIS_ENABLED"] = "false"

from modules.ai.cache_manager import (
    CacheManager,
    MemoryCache,
    cache_manager,
    get_cache,
    set_cache,
    delete_cache,
)


class TestMemoryCacheBasic:
    """get/set/delete/clear on the in-memory LRU."""

    def test_set_and_get(self):
        c = MemoryCache()
        c.set("k", "v", ttl=60)
        assert c.get("k") == "v"

    def test_set_without_ttl_persists(self):
        c = MemoryCache()
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_get_missing_returns_none(self):
        c = MemoryCache()
        assert c.get("never-set") is None

    def test_delete(self):
        c = MemoryCache()
        c.set("k", "v", ttl=60)
        c.delete("k")
        assert c.get("k") is None

    def test_delete_missing_is_noop(self):
        c = MemoryCache()
        # Should not raise
        c.delete("never-existed")

    def test_clear(self):
        c = MemoryCache()
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=60)
        c.set("c", 3, ttl=60)
        c.clear()
        assert c.get("a") is None
        assert c.get("b") is None
        assert c.get("c") is None

    def test_overwrite_value(self):
        c = MemoryCache()
        c.set("k", "v1", ttl=60)
        c.set("k", "v2", ttl=60)
        assert c.get("k") == "v2"


class TestMemoryCacheTTL:
    """Expiry and bounded least-recently-used eviction."""

    @pytest.mark.parametrize("ttl", [None, 0])
    def test_no_expiry_clears_previous_deadline(self, monkeypatch, ttl):
        monkeypatch.setattr(time, "monotonic", lambda: 100)
        c = MemoryCache()
        c.set("k", "old", ttl=1)
        c.set("k", "v", ttl=ttl)
        monkeypatch.setattr(time, "monotonic", lambda: 200)
        assert c.get("k") == "v"

    def test_ttl_expires_at_deadline(self, monkeypatch):
        monkeypatch.setattr(time, "monotonic", lambda: 100)
        c = MemoryCache()
        c.set("k", "v", ttl=1)
        assert c.get("k") == "v"
        monkeypatch.setattr(time, "monotonic", lambda: 101)
        assert c.get("k") is None

    @pytest.mark.parametrize("size", [1, 2, 9, 10])
    def test_small_cache_stays_bounded(self, size):
        c = MemoryCache(max_size=size)
        for i in range(30):
            c.set(str(i), i)
            assert len(c.keys()) <= size
        assert c.get("29") == 29

    def test_overwrite_at_capacity_preserves_other_entries(self):
        c = MemoryCache(max_size=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("b", 3)
        assert c.get("a") == 1
        assert c.get("b") == 3

    def test_expired_keys_reclaimed_before_live_entries(self, monkeypatch):
        monkeypatch.setattr(time, "monotonic", lambda: 100)
        c = MemoryCache(max_size=2)
        c.set("live", 1)
        c.set("expired", 2, ttl=1)
        monkeypatch.setattr(time, "monotonic", lambda: 102)
        c.set("new", 3)
        assert set(c.keys()) == {"live", "new"}

    def test_keys_omit_expired_entries(self, monkeypatch):
        monkeypatch.setattr(time, "monotonic", lambda: 100)
        c = MemoryCache()
        c.set("expired", 1, ttl=1)
        monkeypatch.setattr(time, "monotonic", lambda: 102)
        assert c.keys() == []

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            MemoryCache(max_size=0)

    def test_eviction_on_overflow(self):
        """LRU eviction kicks in when we exceed max_size."""
        c = MemoryCache(max_size=10)
        # Add 15 entries — should evict 10% on the 11th insert
        for i in range(15):
            c.set(f"k{i}", i, ttl=60)
        # Some early keys should be gone
        all_keys = c.keys()
        assert len(all_keys) <= 10
        # Recent keys should still be there
        assert c.get("k14") == 14

    def test_get_refreshes_lru_order(self):
        c = MemoryCache(max_size=2)
        c.set("hot", 1)
        c.set("cold", 2)
        assert c.get("hot") == 1
        c.set("new", 3)
        assert c.get("cold") is None
        assert c.get("hot") == 1
        assert c.get("new") == 3


class TestMemoryCacheKeys:
    """keys(pattern): substring match for clear_pattern support."""

    def test_keys_wildcard_returns_all(self):
        c = MemoryCache()
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=60)
        keys = c.keys("*")
        assert set(keys) == {"a", "b"}

    def test_keys_substring_filter(self):
        c = MemoryCache()
        c.set("user:1:profile", {}, ttl=60)
        c.set("user:2:profile", {}, ttl=60)
        c.set("analytics:1", {}, ttl=60)
        keys = c.keys("user:")
        assert len(keys) == 2
        assert all("user:" in k for k in keys)

    def test_keys_empty_cache(self):
        c = MemoryCache()
        assert c.keys() == []


class TestCacheManagerMakeKey:
    """_make_key: deterministic key from prefix + args + kwargs."""

    def test_key_format(self):
        cm = CacheManager()
        key = cm._make_key("prefix", "a", "b")
        assert key == "prefix:a:b"

    def test_key_kwargs_sorted(self):
        cm = CacheManager()
        k1 = cm._make_key("prefix", "x", foo="a", bar="b")
        k2 = cm._make_key("prefix", "x", bar="b", foo="a")
        # kwarg order shouldn't matter
        assert k1 == k2

    def test_long_key_is_hashed(self):
        cm = CacheManager()
        long_arg = "x" * 500
        key = cm._make_key("prefix", long_arg)
        # Long keys get SHA-256 hashed to keep Redis happy
        assert len(key) < 200
        assert key.startswith("prefix:")


class TestCacheManagerAsync:
    """get/set/delete via the async wrapper (uses in-memory backend)."""

    @pytest.mark.asyncio
    async def test_set_then_get_roundtrip(self):
        cm = CacheManager()
        await cm.set("k1", {"data": "value"})
        result = await cm.get("k1")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        cm = CacheManager()
        result = await cm.get("never-set")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_key(self):
        cm = CacheManager()
        await cm.set("k1", "v1")
        await cm.delete("k1")
        assert await cm.get("k1") is None

    @pytest.mark.asyncio
    async def test_provider_status_helpers(self):
        cm = CacheManager()
        await cm.set_provider_status("openai", {"healthy": True, "latency": 50})
        result = await cm.get_provider_status("openai")
        assert result == {"healthy": True, "latency": 50}

    @pytest.mark.asyncio
    async def test_analytics_helpers(self):
        cm = CacheManager()
        await cm.set_analytics("conversations_per_day", {"2026-06-06": 42}, user_id="u1")
        result = await cm.get_analytics("conversations_per_day", user_id="u1")
        assert result == {"2026-06-06": 42}

    @pytest.mark.asyncio
    async def test_analytics_default_user_is_global(self):
        """When user_id is None, the key falls back to 'global'."""
        cm = CacheManager()
        await cm.set_analytics("total_users", {"count": 100})
        result = await cm.get_analytics("total_users")
        assert result == {"count": 100}

    @pytest.mark.asyncio
    async def test_get_stats(self):
        cm = CacheManager()
        stats = await cm.get_stats()
        assert "redis_enabled" in stats
        # redis is disabled in test env
        assert stats["redis_enabled"] is False
        assert "memory_cache_size" in stats

    @pytest.mark.asyncio
    async def test_clear_pattern_removes_matching_keys(self):
        cm = CacheManager()
        await cm.set("user:1:profile", {})
        await cm.set("user:2:profile", {})
        await cm.set("analytics:1", {})
        await cm.clear_pattern("user:")
        assert await cm.get("user:1:profile") is None
        assert await cm.get("user:2:profile") is None
        # analytics key should remain
        assert await cm.get("analytics:1") == {}


class TestCachedDecorator:
    """The @cached() decorator: function results get cached + reused."""

    @pytest.mark.asyncio
    async def test_caches_function_result(self):
        cm = CacheManager()
        call_count = {"n": 0}

        @cm.cached("test", ttl=60)
        async def expensive_fn(x: int) -> int:
            call_count["n"] += 1
            return x * 2

        r1 = await expensive_fn(5)
        r2 = await expensive_fn(5)
        assert r1 == 10
        assert r2 == 10
        # Should only be called once due to caching
        assert call_count["n"] == 1

    @pytest.mark.asyncio
    async def test_different_args_get_different_cache_entries(self):
        cm = CacheManager()
        call_count = {"n": 0}

        @cm.cached("test", ttl=60)
        async def fn(x: int) -> int:
            call_count["n"] += 1
            return x

        await fn(1)
        await fn(2)
        await fn(1)  # cache hit
        assert call_count["n"] == 2


class TestModuleGlobals:
    """The module-level cache_manager singleton and convenience fns."""

    @pytest.mark.asyncio
    async def test_global_cache_manager_exists(self):
        # Singleton is created at module load
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)

    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        await set_cache("conv:k", "conv:v", ttl=10)
        assert await get_cache("conv:k") == "conv:v"
        await delete_cache("conv:k")
        assert await get_cache("conv:k") is None


class TestCacheManagerInitialize:
    """initialize() with no Redis should fall back to in-memory."""

    @pytest.mark.asyncio
    async def test_initialize_disabled_redis_falls_back(self):
        cm = CacheManager()
        # _enabled starts False (REDIS_ENABLED=false in test env)
        assert cm._enabled is False
        await cm.initialize()
        # After init, _initialized is True and Redis is still None
        assert cm._initialized is True
        assert cm._redis is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
