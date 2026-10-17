"""
Shared synchronous HTTP client for the ANT backend.
Reuses connection pools for synchronous routes. Async callers must offload
requests from the event loop; ``close_client`` offloads socket cleanup.

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

import asyncio
import logging
import threading

import httpx
from lib.public_network import check_public_url, PublicTransport

logger = logging.getLogger("lib.http_client")

def validate_url(url: str, skip_ssrf_check: bool = False) -> None:
    """Raise ValueError if ``url`` points at a private IP range.

    Used by ``SyncHTTPClient`` to block SSRF attempts unless the caller
    explicitly opts out (local Ollama).
    """
    if not skip_ssrf_check:
        check_public_url(url)



class SyncHTTPClient:
    """Thin wrapper around ``httpx.Client`` that adds an SSRF guard.

    Exposes ``get``, ``post``, ``delete``, ``stream``, and ``close`` —
    the subset used by ``core/main.py`` and ``modules/platform/cloud_providers.py``.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=httpx.Timeout(30.0), transport=PublicTransport(), trust_env=False)
        self._local_client = httpx.Client(timeout=httpx.Timeout(30.0), trust_env=False)

    def _get_client(self, local: bool) -> httpx.Client:
        # Keep this wrapper's identity stable for modules that import it directly.
        # Reopen a pool only when a later application lifespan makes a request.
        with self._lock:
            if local:
                if self._local_client is None:
                    self._local_client = httpx.Client(timeout=httpx.Timeout(30.0), trust_env=False)
                return self._local_client
            if self._client is None:
                self._client = httpx.Client(timeout=httpx.Timeout(30.0), transport=PublicTransport(), trust_env=False)
            return self._client

    def _check(self, url: str, skip_ssrf_check: bool) -> None:
        validate_url(url, skip_ssrf_check=skip_ssrf_check)

    def get(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        if kwargs.get("follow_redirects"):
            raise ValueError("Automatic redirects are disabled")
        client = self._get_client(skip_ssrf_check)
        return client.get(url, **kwargs)

    def post(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        if kwargs.get("follow_redirects"):
            raise ValueError("Automatic redirects are disabled")
        client = self._get_client(skip_ssrf_check)
        streaming = kwargs.pop("stream", False)
        if streaming:
            request = client.build_request("POST", url, **kwargs)
            return client.send(request, stream=True)
        return client.post(url, **kwargs)

    def delete(self, url: str, *, skip_ssrf_check: bool = False, **kwargs) -> httpx.Response:
        self._check(url, skip_ssrf_check)
        if kwargs.get("follow_redirects"):
            raise ValueError("Automatic redirects are disabled")
        client = self._get_client(skip_ssrf_check)
        return client.delete(url, **kwargs)

    def stream(self, method: str, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        self._check(url, skip_ssrf_check)
        if kwargs.get("follow_redirects"):
            raise ValueError("Automatic redirects are disabled")
        client = self._get_client(skip_ssrf_check)
        return client.stream(method, url, **kwargs)

    def close(self) -> None:
        with self._lock:
            clients = (self._client, self._local_client)
            self._client = self._local_client = None
        for client in clients:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    # One failed pool must not prevent cleanup of the other.
                    logger.warning("HTTP connection pool cleanup failed")


# Process-wide synchronous client. Instantiated at module import — call sites
# do ``sync_client.get(...)``, not ``sync_client().get(...)``.
sync_client: SyncHTTPClient = SyncHTTPClient()


def get_client() -> SyncHTTPClient:
    """Return the process-wide synchronous client."""
    return sync_client


async def close_client() -> None:
    """Async-safe shutdown hook. Called from the FastAPI lifespan exit.

    The wrapper remains shared by all importers. It creates fresh connection
    pools on the next request, without opening unused pools during shutdown.
    Synchronous socket cleanup runs off the event loop.
    """
    try:
        await asyncio.to_thread(sync_client.close)
    except Exception:  # pragma: no cover - best-effort cleanup
        logger.warning("Shared HTTP client cleanup failed")
