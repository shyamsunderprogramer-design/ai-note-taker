"""Connect only to resolved public addresses, retaining the hostname for TLS.

Resolving and then connecting to that numeric address prevents DNS rebinding.
Environment proxies are disabled by the clients using these backends.
"""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpcore
import httpx


def check_public_url(url):
    parsed = urlsplit(str(url))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("An HTTP(S) URL with a hostname is required")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL credentials are not allowed")
    if "%" in parsed.hostname or "\\" in str(url):
        raise ValueError("Ambiguous hostname is not allowed")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if not addr.is_global or (getattr(addr, "ipv4_mapped", None) and not getattr(addr, "ipv4_mapped", None).is_global):
        raise ValueError("Non-public destination is not allowed")


def public_addresses(records):
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses:
        raise ValueError("Destination has no addresses")
    for host in addresses:
        addr = ipaddress.ip_address(host)
        if not addr.is_global or (getattr(addr, "ipv4_mapped", None) and not getattr(addr, "ipv4_mapped", None).is_global):
            raise ValueError("Non-public destination is not allowed")
    return addresses


class PublicBackend(httpcore.SyncBackend):
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        addresses = public_addresses(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        return super().connect_tcp(addresses[0], port, timeout, local_address, socket_options)


class AsyncPublicBackend(httpcore.AnyIOBackend):
    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout)
        addresses = public_addresses(records)
        return await super().connect_tcp(addresses[0], port, timeout, local_address, socket_options)


class PublicTransport(httpx.HTTPTransport):
    def __init__(self):
        super().__init__(trust_env=False)
        self._pool._network_backend = PublicBackend()


class AsyncPublicTransport(httpx.AsyncHTTPTransport):
    def __init__(self):
        super().__init__(trust_env=False)
        self._pool._network_backend = AsyncPublicBackend()


def public_async_client():
    return httpx.AsyncClient(transport=AsyncPublicTransport(), trust_env=False, follow_redirects=False)
