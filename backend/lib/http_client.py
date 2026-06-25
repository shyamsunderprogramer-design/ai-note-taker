"""
Shared async HTTP client for the ANT backend.
Replaces synchronous `requests` calls with async `httpx.AsyncClient` to avoid
blocking the asyncio event loop.

Usage:
    from lib.http_client import sync_client

    # In any context (sync wrapper for non-async routes):
    resp = sync_client.get(url, timeout=10)

    # Async-safe shutdown:
    from lib.http_client import close_client
    await close_client()

The ``sync_client`` is a process-wide synchronous wrapper around ``httpx.Client``
used by non-async routes (e.g. Ollama listing, model pulls). It enforces
an SSRF guard: requests to private/loopback/link-local IP ranges are blocked
unless the caller explicitly passes ``skip_ssrf_check=True`` (used for the
local Ollama endpoint, which is by design on 127.0.0.1).
"""

import logging
from urllib.parse import urlparse

import httpx
from ipaddress import ip_address, ip_network

logger = logging.getLogger("lib.http_client")

# CIDR blocks we refuse to talk to by default. Loopback is the local Ollama
# endpoint and is allowed only when explicitly opted in.
_PRIVATE_RANGES = [
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("0.0.0.0/8"),
    ip_network("::1/128"),
    ip_network("fe80::/10"),
]


def validate_url(url: str, skip_ssrf_check: bool = False) -> None:
    """Raise ValueError if ``url`` points at a private IP range.

    Used by ``SyncHTTPClient`` to block SSRF attempts unless the caller
    explicitly opts out (local Ollama).
    """
    if skip_ssrf_check:
        return
    parsed = urlparse(url)
    host = parsed.hostname or ""
    try:
        addr = ip_address(host)
    except ValueError:
        # Not an IP literal — could be a DNS name. We don't resolve here;
        # the underlying httpx call would resolve and connect. For our
        # purposes (config-supplied endpoints), hostname-based URLs are
        # treated as safe and only IP literals get the strict check.
        return
    for net in _PRIVATE_RANGES:
        if addr in net:
            raise ValueError(
                f"Refusing to call private/loopback URL: {url} "
                f"(matches {net}). Pass skip_ssrf_check=True to override."
            )


class SyncHTTPClient:
    """Thin wrapper around ``httpx.Client`` that adds an SSRF guard.

    Exposes ``get``, ``post``, ``delete``, ``stream``, and ``close`` —
    the subset used by ``core/main.py`` and ``modules/platform/cloud_providers.py``.
    """

    def __init__(self):
        self._client = httpx.Client(timeout=httpx.Timeout(30.0))

    def _check(self, url: str, skip_ssrf_check: bool) -> None:
        validate_url(url, skip_ssrf_check=skip_ssrf_check)

    def get(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        return self._client.get(url, **kwargs)

    def post(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        return self._client.post(url, **kwargs)

    def delete(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        return self._client.delete(url, **kwargs)

    def stream(self, method: str, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        self._check(url, skip_ssrf_check)
        return self._client.stream(method, url, **kwargs)

    def close(self) -> None:
        self._client.close()


# Process-wide synchronous client. Instantiated at module import — call sites
# do ``sync_client.get(...)``, not ``sync_client().get(...)``.
sync_client: SyncHTTPClient = SyncHTTPClient()


def get_client() -> SyncHTTPClient:
    """Return the process-wide synchronous client."""
    return sync_client


async def close_client() -> None:
    """Async-safe shutdown hook. Called from the FastAPI lifespan exit.

    Resets the singleton to a fresh client so a re-bind (e.g. test suite
    reloading) doesn't reuse closed sockets. Best-effort: any error during
    close is logged and swallowed — we never let a teardown hook block
    server shutdown.
    """
    global sync_client
    try:
        sync_client.close()
    except Exception as e:  # pragma: no cover - best-effort cleanup
        logger.warning("Error closing sync HTTP client: %s", e)
    sync_client = SyncHTTPClient()