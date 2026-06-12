"""
Rate limiting module
Prevents API abuse and ensures fair usage
"""

import os
import time
import asyncio
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import functools

try:
    from fastapi import Request, HTTPException, status
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@dataclass
class RateLimitEntry:
    """Rate limit tracking for a single client"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)


class RateLimiter:
    """
    Rate limiter with configurable windows and limits
    Default: 100 requests per minute per IP
    """

    def __init__(self, requests_per_minute: int = 100, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._storage: Dict[str, RateLimitEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup()

    def _start_cleanup(self):
        """Start the cleanup background task"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(self._cleanup_old_entries())
        except RuntimeError:
            pass  # No event loop running yet, cleanup will be handled lazily

    async def _cleanup_old_entries(self):
        """Remove old entries every 5 minutes"""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            current_time = time.time()
            cutoff = current_time - (self.window_seconds * 2)

            keys_to_remove = [
                key for key, entry in self._storage.items()
                if entry.window_start < cutoff
            ]
            for key in keys_to_remove:
                del self._storage[key]

    def _get_key(self, identifier: str, path: Optional[str] = None) -> str:
        """Generate a storage key"""
        if path:
            return f"{identifier}:{path}"
        return identifier

    async def is_allowed(self, identifier: str, path: Optional[str] = None) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed
        Returns: (allowed, headers_dict)
        """
        async with self._lock:
            key = self._get_key(identifier, path)
            current_time = time.time()

            if key not in self._storage:
                self._storage[key] = RateLimitEntry(
                    requests=1,
                    window_start=current_time,
                    last_request=current_time
                )
                return True, self._get_headers(1, current_time)

            entry = self._storage[key]
            time_passed = current_time - entry.window_start

            # Reset window if expired
            if time_passed > self.window_seconds:
                entry.requests = 1
                entry.window_start = current_time
                entry.last_request = current_time
                return True, self._get_headers(1, current_time)

            # Check limit
            entry.requests += 1
            entry.last_request = current_time

            headers = self._get_headers(entry.requests, entry.window_start)

            if entry.requests > self.requests_per_minute:
                return False, headers

            return True, headers

    def _get_headers(self, current_requests: int, window_start: float) -> Dict[str, Any]:
        """Generate rate limit headers"""
        reset_time = window_start + self.window_seconds
        remaining = max(0, self.requests_per_minute - current_requests)

        return {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(reset_time)),
            "X-RateLimit-Window": str(self.window_seconds),
        }

    async def get_wait_time(self, identifier: str, path: Optional[str] = None) -> float:
        """Get seconds until rate limit resets"""
        async with self._lock:
            key = self._get_key(identifier, path)
            entry = self._storage.get(key)
            if not entry:
                return 0.0

            reset_time = entry.window_start + self.window_seconds
            wait_time = reset_time - time.time()
            return max(0.0, wait_time)


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
    window_seconds=60
)


def rate_limit(requests_per_minute: int = 100, window_seconds: int = 60):
    """
    Decorator for rate limiting specific endpoints

    Usage:
        @app.get("/api/data")
        @rate_limit(requests_per_minute=10)
        async def get_data():
            return {"data": "value"}
    """
    limiter = RateLimiter(requests_per_minute, window_seconds)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract request from args
            request = None
            for arg in args:
                if HAS_FASTAPI and isinstance(arg, Request):
                    request = arg
                    break

            if request:
                client_ip = request.client.host if request.client else "unknown"
                allowed, headers = await limiter.is_allowed(client_ip, request.url.path)

                if not allowed:
                    wait_time = await limiter.get_wait_time(client_ip, request.url.path)
                    if HAS_FASTAPI:
                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "Rate limit exceeded",
                                "retry_after": int(wait_time),
                                "limit": requests_per_minute,
                                "window": window_seconds
                            },
                            headers={"Retry-After": str(int(wait_time)), **headers}
                        )

                # Store headers in request state for middleware
                if hasattr(request, 'state'):
                    request.state.rate_limit_headers = headers

            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        return wrapper
    return decorator


if HAS_FASTAPI:
    class RateLimitMiddleware(BaseHTTPMiddleware):
        """
        FastAPI middleware for global rate limiting
        Apply to all routes automatically
        """

        def __init__(self, app, requests_per_minute: int = 100, window_seconds: int = 60):
            super().__init__(app)
            self.limiter = RateLimiter(requests_per_minute, window_seconds)
            self.requests_per_minute = requests_per_minute
            self.window_seconds = window_seconds

        async def dispatch(self, request: Request, call_next) -> Response:
            # Skip rate limiting for certain paths
            if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
                return await call_next(request)

            # Get client identifier (IP or user ID if authenticated)
            client_id = request.client.host if request.client else "unknown"

            # Check if user has custom rate limit (admin users)
            if hasattr(request.state, 'current_user'):
                user = request.state.current_user
                if user and getattr(user, 'is_admin', False):
                    # Admins bypass rate limiting
                    response = await call_next(request)
                    response.headers["X-RateLimit-Limit"] = "UNLIMITED"
                    return response

            allowed, headers = await self.limiter.is_allowed(client_id, request.url.path)

            if not allowed:
                wait_time = await self.limiter.get_wait_time(client_id, request.url.path)
                return Response(
                    content=f'{{"error": "Rate limit exceeded", "retry_after": {int(wait_time)}}}',
                    status_code=429,
                    headers={
                        "Content-Type": "application/json",
                        "Retry-After": str(int(wait_time)),
                        **headers
                    }
                )

            response = await call_next(request)

            # Add rate limit headers to response
            for key, value in headers.items():
                response.headers[key] = str(value)

            return response


# Convenience function for FastAPI
def rate_limit_middleware(app, requests_per_minute: int = 100, window_seconds: int = 60):
    """Add rate limiting middleware to FastAPI app"""
    if HAS_FASTAPI:
        return RateLimitMiddleware(app, requests_per_minute, window_seconds)
    return None


# Rate limit tiers
TIER_LIMITS = {
    "free": 100,      # 100 requests/min
    "basic": 500,     # 500 requests/min
    "pro": 2000,      # 2000 requests/min
    "enterprise": 10000,  # 10000 requests/min
}
