"""
Test suite for backend/security/rate_limit.py
Covers RateLimitEntry dataclass and the RateLimiter state machine.

The RateLimiter has a background cleanup task that starts on
construction (`_start_cleanup`). In tests there's no running event
loop, so this becomes a no-op (it catches RuntimeError). The task
itself is never exercised, so we don't need to mock it.

Run with: python -m pytest backend/tests/test_security_rate_limit.py -v
"""

import asyncio
import os
import sys

import pytest

# Add backend/ to sys.path so `from security.rate_limit import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from security.rate_limit import (  # noqa: E402
    RateLimitEntry,
    RateLimiter,
    TIER_LIMITS,
)


class TestRateLimitEntry:
    """RateLimitEntry dataclass: defaults, mutable state."""

    def test_default_construction(self):
        e = RateLimitEntry()
        assert e.requests == 0  # nosec B101
        assert e.window_start > 0  # nosec B101
        assert e.last_request > 0  # nosec B101

    def test_window_start_defaults_to_now(self):
        import time
        e = RateLimitEntry()
        # Should be very close to current time
        assert abs(e.window_start - time.time()) < 1.0  # nosec B101

    def test_mutable_fields(self):
        e = RateLimitEntry()
        e.requests = 5
        e.window_start = 1000.0
        e.last_request = 1001.0
        assert e.requests == 5  # nosec B101
        assert e.window_start == 1000.0  # nosec B101
        assert e.last_request == 1001.0  # nosec B101


class TestRateLimiterKeyGeneration:
    """RateLimiter._get_key: with and without path."""

    def test_key_without_path_is_identifier(self):
        rl = RateLimiter()
        assert rl._get_key("1.2.3.4") == "1.2.3.4"  # nosec B101

    def test_key_with_path_concatenates(self):
        rl = RateLimiter()
        assert rl._get_key("1.2.3.4", "/api/x") == "1.2.3.4:/api/x"  # nosec B101

    def test_different_paths_produce_different_keys(self):
        rl = RateLimiter()
        k1 = rl._get_key("ip", "/api/a")
        k2 = rl._get_key("ip", "/api/b")
        assert k1 != k2  # nosec B101


class TestRateLimiterAllowDeny:
    """RateLimiter.is_allowed: first request, N requests, limit + 1."""

    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=60)
        allowed, headers = await rl.is_allowed("client-1", "/api/test")
        assert allowed is True  # nosec B101
        assert headers["X-RateLimit-Limit"] == "10"  # nosec B101
        assert headers["X-RateLimit-Remaining"] == "9"  # nosec B101

    @pytest.mark.asyncio
    async def test_requests_under_limit_allowed(self):
        rl = RateLimiter(requests_per_minute=5, window_seconds=60)
        for i in range(5):
            allowed, _ = await rl.is_allowed("client-1", "/api/test")
            assert allowed is True, f"Request {i+1} should be allowed"  # nosec B101

    @pytest.mark.asyncio
    async def test_request_over_limit_denied(self):
        rl = RateLimiter(requests_per_minute=3, window_seconds=60)
        # First 3 should be allowed
        for _ in range(3):
            allowed, _ = await rl.is_allowed("client-1", "/api/test")
            assert allowed is True  # nosec B101
        # 4th should be denied
        allowed, headers = await rl.is_allowed("client-1", "/api/test")
        assert allowed is False  # nosec B101
        assert headers["X-RateLimit-Remaining"] == "0"  # nosec B101

    @pytest.mark.asyncio
    async def test_different_clients_have_independent_buckets(self):
        rl = RateLimiter(requests_per_minute=2, window_seconds=60)
        # Client A burns their quota
        await rl.is_allowed("client-A", "/x")
        await rl.is_allowed("client-A", "/x")
        allowed_a, _ = await rl.is_allowed("client-A", "/x")
        assert allowed_a is False  # nosec B101
        # Client B is untouched
        allowed_b, _ = await rl.is_allowed("client-B", "/x")
        assert allowed_b is True  # nosec B101

    @pytest.mark.asyncio
    async def test_different_paths_independent(self):
        rl = RateLimiter(requests_per_minute=2, window_seconds=60)
        await rl.is_allowed("client", "/path-a")
        await rl.is_allowed("client", "/path-a")
        # /path-a is exhausted
        allowed_a, _ = await rl.is_allowed("client", "/path-a")
        assert allowed_a is False  # nosec B101
        # /path-b is untouched
        allowed_b, _ = await rl.is_allowed("client", "/path-b")
        assert allowed_b is True  # nosec B101


class TestRateLimiterHeaders:
    """RateLimiter._get_headers: limit, remaining, reset, window."""

    def test_remaining_decreases_with_count(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=60)
        h1 = rl._get_headers(1, 1000.0)
        h5 = rl._get_headers(5, 1000.0)
        h9 = rl._get_headers(9, 1000.0)
        assert h1["X-RateLimit-Remaining"] == "9"  # nosec B101
        assert h5["X-RateLimit-Remaining"] == "5"  # nosec B101
        assert h9["X-RateLimit-Remaining"] == "1"  # nosec B101

    def test_remaining_clamped_at_zero(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=60)
        h = rl._get_headers(20, 1000.0)  # Way over the limit
        assert h["X-RateLimit-Remaining"] == "0"  # nosec B101

    def test_reset_is_window_start_plus_window(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=60)
        h = rl._get_headers(1, 1000.0)
        # reset = 1000 + 60 = 1060
        assert h["X-RateLimit-Reset"] == "1060"  # nosec B101

    def test_window_string_matches_config(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=30)
        h = rl._get_headers(1, 0.0)
        assert h["X-RateLimit-Window"] == "30"  # nosec B101


class TestRateLimiterWindowExpiry:
    """RateLimiter: window resets after window_seconds elapsed."""

    @pytest.mark.asyncio
    async def test_window_resets_after_expiry(self, monkeypatch):
        rl = RateLimiter(requests_per_minute=2, window_seconds=60)
        # Use real time.time() but advance it virtually
        import time
        real_time = time.time
        current = [1000.0]
        monkeypatch.setattr(time, "time", lambda: current[0])

        # Two requests in window 1
        allowed, _ = await rl.is_allowed("client", "/x")
        assert allowed is True  # nosec B101
        allowed, _ = await rl.is_allowed("client", "/x")
        assert allowed is True  # nosec B101
        # Third request in window 1 denied
        allowed, _ = await rl.is_allowed("client", "/x")
        assert allowed is False  # nosec B101

        # Advance time past the window (60 + 1 seconds later)
        current[0] = 1061.0
        # Next request should reset the window and be allowed
        allowed, headers = await rl.is_allowed("client", "/x")
        assert allowed is True  # nosec B101
        assert headers["X-RateLimit-Remaining"] == "1"  # nosec B101


class TestRateLimiterWaitTime:
    """RateLimiter.get_wait_time: 0 for never-seen, positive for active."""

    @pytest.mark.asyncio
    async def test_get_wait_time_no_entry_returns_zero(self):
        rl = RateLimiter()
        wait = await rl.get_wait_time("never-seen", "/x")
        assert wait == 0.0  # nosec B101

    @pytest.mark.asyncio
    async def test_get_wait_time_active_window(self):
        rl = RateLimiter(requests_per_minute=10, window_seconds=60)
        await rl.is_allowed("client", "/x")
        wait = await rl.get_wait_time("client", "/x")
        # Should be roughly the window seconds (60) — less if time has passed
        assert 0 < wait <= 60  # nosec B101


class TestRateLimiterTierLimits:
    """TIER_LIMITS: well-known tier names map to expected values."""

    def test_free_tier_is_100(self):
        assert TIER_LIMITS["free"] == 100  # nosec B101

    def test_basic_tier_is_500(self):
        assert TIER_LIMITS["basic"] == 500  # nosec B101

    def test_pro_tier_is_2000(self):
        assert TIER_LIMITS["pro"] == 2000  # nosec B101

    def test_enterprise_tier_is_10000(self):
        assert TIER_LIMITS["enterprise"] == 10000  # nosec B101

    def test_all_tiers_are_positive(self):
        for tier, limit in TIER_LIMITS.items():
            assert limit > 0, f"Tier {tier} has non-positive limit"  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
