"""
Shared async HTTP client for the ANT backend.
Replaces synchronous `requests` calls with async `httpx.AsyncClient` to avoid
blocking the asyncio event loop.

Usage:
    from lib.http_client import http_client, get_client

    # In async context:
    resp = await http_client.post(url, json=data)

    # For SSE streaming (returns async iterator):
    async with http_client.stream("POST", url, json=data) as resp:
        async for line in resp.aiter_lines():
            ...
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger("http_client")

# Singleton async client — created on first use, lives for the process lifetime.
# Connection pooling and keep-alive are handled automatically.
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create the shared async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
        )
    return _client


async def close_client():
    """Gracefully close the shared client (call on app shutdown)."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


class SyncHTTPClient:
    """Synchronous wrapper for contexts where async is not available (e.g., non-async functions).

    For new code, prefer using `await get_client()` directly.
    This exists as a bridge during the migration from `requests` to `httpx`.
    """

    def __init__(self):
        self._client: Optional[httpx.Client] = None

    def _get(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
                follow_redirects=True,
            )
        return self._client

    def post(self, url, **kwargs):
        return self._get().post(url, **kwargs)

    def get(self, url, **kwargs):
        return self._get().get(url, **kwargs)

    def delete(self, url, **kwargs):
        return self._get().delete(url, **kwargs)

    def stream(self, method, url, **kwargs):
        return self._get().stream(method, url, **kwargs)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# Module-level sync client for legacy code
sync_client = SyncHTTPClient()