import socket
from unittest.mock import AsyncMock, patch

import pytest

from lib.public_network import AsyncPublicBackend, PublicBackend, check_public_url, public_addresses


@pytest.mark.parametrize("url", [
    "http://127.0.0.1", "http://10.0.0.1", "http://169.254.169.254",
    "http://[::1]", "http://[fc00::1]", "http://[::ffff:127.0.0.1]",
    "file:///etc/passwd", "https://user:secret@example.com", "http://[fe80::1%25en0]",
])
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        check_public_url(url)


def records(*addresses):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, 443)) for a in addresses]


def test_rejects_mixed_public_and_private_dns():
    with pytest.raises(ValueError):
        public_addresses(records("8.8.8.8", "127.0.0.1"))


def test_connection_uses_validated_numeric_address_not_second_dns_lookup():
    with patch("socket.getaddrinfo", return_value=records("8.8.8.8")), patch(
        "httpcore.SyncBackend.connect_tcp", return_value="stream"
    ) as connect:
        assert PublicBackend().connect_tcp("example.com", 443) == "stream"
    assert connect.call_args.args[:2] == ("8.8.8.8", 443)


def test_private_dns_never_connects():
    with patch("socket.getaddrinfo", return_value=records("10.0.0.1")), patch(
        "httpcore.SyncBackend.connect_tcp"
    ) as connect:
        with pytest.raises(ValueError):
            PublicBackend().connect_tcp("attacker.example", 443)
    connect.assert_not_called()


@pytest.mark.asyncio
async def test_async_connection_pins_public_address():
    with patch("asyncio.BaseEventLoop.getaddrinfo", new_callable=AsyncMock,
               return_value=records("8.8.8.8")), patch(
        "httpcore.AnyIOBackend.connect_tcp", new_callable=AsyncMock, return_value="stream"
    ) as connect:
        assert await AsyncPublicBackend().connect_tcp("example.com", 443) == "stream"
    assert connect.call_args.args[:2] == ("8.8.8.8", 443)


@pytest.mark.asyncio
async def test_async_private_dns_never_connects():
    with patch("asyncio.BaseEventLoop.getaddrinfo", new_callable=AsyncMock,
               return_value=records("8.8.8.8", "127.0.0.1")), patch(
        "httpcore.AnyIOBackend.connect_tcp", new_callable=AsyncMock
    ) as connect:
        with pytest.raises(ValueError):
            await AsyncPublicBackend().connect_tcp("attacker.example", 443)
    connect.assert_not_called()
