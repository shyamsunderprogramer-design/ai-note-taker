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
import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("http_client")

# ---------------------------------------------------------------------------
# SSRF protection — validate URLs before making outbound requests
# ---------------------------------------------------------------------------

# Schemes that are allowed for outbound HTTP requests
_ALLOWED_SCHEMES = {"http", "https"}

# Private/internal IP ranges that must never be reached from user-supplied URLs
_PRIVATE_NETWORKS = [
    # IPv4 loopback
    ipaddress.ip_network("127.0.0.0/8"),
    # IPv4 link-local
    ipaddress.ip_network("169.254.0.0/16"),
    # IPv4 RFC1918 private ranges
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # IPv4 unspecified / "this network"
    ipaddress.ip_network("0.0.0.0/8"),
    # IPv6 loopback and link-local
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str) -> str:
    """Validate a URL to prevent SSRF attacks.

    Ensures the URL:
    - Uses http:// or https:// scheme
    - Does not resolve to a private/internal IP address
    - Does not use dangerous schemes like file://, ftp://, etc.

    Returns the validated URL string.
    Raises ValueError if the URL is invalid or points to a private network.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string")

    parsed = urlparse(url.strip())

    # Check scheme
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(
            "URL scheme is not allowed. Only http:// and https:// are permitted."
        )

    # Must have a hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname")

    # SECURITY: Block credential injection attempts (user@host patterns)
    if "@" in url.strip():
        raise ValueError("URLs containing credentials are not allowed")

    # Block obvious localhost variations
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "localhost.localdomain", "0.0.0.0", "::"):
        raise ValueError("Requests to localhost are not allowed")

    # SECURITY: Resolve the hostname to detect private IP addresses
    # This prevents SSRF attacks where an attacker uses a domain that resolves
    # to internal addresses like 169.254.169.254 (cloud metadata)
    import socket
    try:
        # getaddrinfo resolves DNS and returns all IP addresses
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        # Validate port is within valid range
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("Invalid port number")
        addr_infos = socket.getaddrinfo(hostname, port)
        for family, _type, _proto, _canon, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                # If it's not a valid IP (e.g. Unix socket path), block it
                raise ValueError(f"URL hostname resolves to invalid address: {ip_str}")
            for private_net in _PRIVATE_NETWORKS:
                if ip in private_net:
                    raise ValueError(
                        f"URL resolves to private/internal IP address {ip_str}, which is not allowed"
                    )
    except socket.gaierror:
        # DNS resolution failed — could be a bad domain, let it through
        # (the HTTP request will fail anyway)
        pass

    return url

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

    def post(self, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        # SECURITY: Validate URL to prevent SSRF attacks
        validated_url = url if skip_ssrf_check else validate_url(url)
        return self._get().post(validated_url, **kwargs)

    def get(self, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        # SECURITY: Validate URL to prevent SSRF attacks
        validated_url = url if skip_ssrf_check else validate_url(url)
        return self._get().get(validated_url, **kwargs)

    def delete(self, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        # SECURITY: Validate URL to prevent SSRF attacks
        validated_url = url if skip_ssrf_check else validate_url(url)
        return self._get().delete(validated_url, **kwargs)

    def stream(self, method: str, url: str, *, skip_ssrf_check: bool = False, **kwargs):
        # SECURITY: Validate URL to prevent SSRF attacks
        validated_url = url if skip_ssrf_check else validate_url(url)
        return self._get().stream(method, validated_url, **kwargs)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# Module-level sync client for legacy code
sync_client = SyncHTTPClient()