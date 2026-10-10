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


_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_IPV4_SPECIAL = ipaddress.ip_network("192.0.0.0/24")


def is_public_address(addr):
    """Require public unicast, including the target behind IPv6 translation.

    Python 3.12 classifies some multicast, legacy site-local and transition
    addresses as global. They must not provide a route around the SSRF guard.
    """
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped:
            return is_public_address(addr.ipv4_mapped)
        if addr in _NAT64:
            return is_public_address(ipaddress.IPv4Address(int(addr) & 0xffffffff))
        if addr.sixtofour or addr.teredo or addr.is_site_local:
            return False
    elif addr in _IPV4_SPECIAL and str(addr) not in {"192.0.0.9", "192.0.0.10"}:
        return False
    return addr.is_global and not addr.is_multicast and not addr.is_reserved


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
    if not is_public_address(addr):
        raise ValueError("Non-public destination is not allowed")


def public_addresses(records):
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses:
        raise ValueError("Destination has no addresses")
    for host in addresses:
        addr = ipaddress.ip_address(host)
        if not is_public_address(addr):
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
