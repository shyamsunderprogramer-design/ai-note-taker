"""Jira accepts public installations while rejecting ambiguous destinations."""
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from routes import jira


@pytest.mark.parametrize("base_url", [
    "https://team.atlassian.net", "https://jira.example.com/",
    "https://jira.example.com:443/tools/jira/",
    "https://jira.example.com./jira", "https://xn--bcher-kva.example/jira",
    "https://jira.example.com/team%20one/jira", "https://jira.example.com/%E6%97%A5",
    "https://8.8.8.8/jira", "https://[2606:4700:4700::1111]/jira",
    "https://[::ffff:8.8.8.8]:443/jira",
])
def test_public_origins_and_installation_contexts(base_url):
    assert jira._jira_api_url(base_url, "/serverInfo") == base_url.rstrip("/") + "/rest/api/3/serverInfo"


@pytest.mark.parametrize("base_url", [
    None, 123, {}, [], "", "http://jira.example.com", "//jira.example.com",
    "https://jira.example.com:8443", "https://jira.example.com:443@attacker.example",
    "https://user:secret@jira.example.com", "https://jira.example.com?next=attacker",
    "https://jira.example.com#@attacker.example", "https://jira.example.com\\@attacker.example",
    "https://jira.example.com\n.attacker.example", " https://jira.example.com",
    "https://jira.example.com/\tcontext", "https://jira.example.com/\x00context",
    "https://jira.example.com/%0d%0aHost:attacker.example", "https://jira.example.com/%7f",
    "https://jira.example.com/%2f%2fattacker.example", "https://jira.example.com/%5c",
    "https://jira.example.com/../private", "https://jira.example.com/%2e%2e/private",
    "https://jira.example.com/%252e%252e/private", "https://jira.example.com/%XX",
    "https://jira.example.com/%FF", "https://jira.example.com/" + "a" * 2048,
    "https://-invalid.example", "https://jira..example.com", "https://[invalid]",
    "https://jira%2eexample.com", "https://127.0.0.1", "https://10.0.0.1",
    "https://169.254.169.254", "https://[::1]", "https://[::ffff:127.0.0.1]",
    "https://[64:ff9b::a00:1]", "https://[fe80::1%25en0]",
])
def test_rejects_unsafe_or_ambiguous_base_urls(base_url):
    with pytest.raises(HTTPException) as error:
        jira._jira_api_url(base_url, "/serverInfo")
    assert error.value.status_code == 400
    assert error.value.detail == "A public HTTPS Jira URL is required"


def connection_payload(base_url):
    return {"base_url": base_url, "email": "synthetic@example.com", "api_token": "synthetic-test-token"}


@pytest.mark.asyncio
async def test_connect_cannot_follow_redirects_or_save_redirecting_servers(monkeypatch):
    requests = []

    def redirect(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"})

    # Replace only the transport: exercise the actual client factory and its
    # redirect/proxy settings. No external requests or credentials are used.
    monkeypatch.setattr("lib.public_network.AsyncPublicTransport", lambda: httpx.MockTransport(redirect))
    save = AsyncMock()
    monkeypatch.setattr(jira, "save_integration_config", save)
    with pytest.raises(HTTPException) as error:
        await jira.connect_jira(connection_payload("https://jira.example.com"), SimpleNamespace(id="synthetic"))
    assert error.value.status_code == 400
    assert len(requests) == 1
    assert str(requests[0].url) == "https://jira.example.com/rest/api/3/serverInfo"
    save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("addresses", [["127.0.0.1"], ["8.8.8.8", "10.0.0.1"]])
async def test_connect_rejects_private_dns_before_socket_or_config_write(monkeypatch, addresses):
    records = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses]
    monkeypatch.setattr("asyncio.BaseEventLoop.getaddrinfo", AsyncMock(return_value=records))
    connect = AsyncMock()
    monkeypatch.setattr("httpcore.AnyIOBackend.connect_tcp", connect)
    save = AsyncMock()
    monkeypatch.setattr(jira, "save_integration_config", save)
    with pytest.raises(HTTPException) as error:
        await jira.connect_jira(connection_payload("https://jira.example.com"), SimpleNamespace(id="synthetic"))
    assert error.value.status_code == 502
    connect.assert_not_awaited()
    save.assert_not_awaited()
