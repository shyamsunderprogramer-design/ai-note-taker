"""Shared HTTP pools survive a new lifespan without stale imported references."""
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import httpx
import pytest

from lib import http_client
from lib.public_network import PublicTransport


@pytest.fixture
def client_factory(monkeypatch):
    created, options = [], []
    real_client = httpx.Client

    def create(**kwargs):
        options.append(kwargs)
        pool_id = len(created)
        client = real_client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"pool": pool_id})), trust_env=False)
        created.append(client)
        return client

    monkeypatch.setattr(http_client.httpx, 'Client', create)
    client = http_client.SyncHTTPClient()
    monkeypatch.setattr(http_client, 'sync_client', client)
    yield client, created, options
    client.close()
    for pool in created:
        pool.close()


@pytest.mark.asyncio
async def test_imported_wrapper_reopens_only_requested_pools(client_factory):
    client, pools, options = client_factory
    from lib.http_client import sync_client as imported
    await http_client.close_client()
    assert all(pool.is_closed for pool in pools)
    assert len(pools) == 2  # Shutdown must not open replacement pools.
    assert http_client.get_client() is imported is client
    assert imported.get('https://example.com/model').json() == {'pool': 2}
    assert imported.post('http://127.0.0.1/model', skip_ssrf_check=True).json() == {'pool': 3}
    assert isinstance(options[2]['transport'], PublicTransport)
    assert 'transport' not in options[3]
    assert all(option['trust_env'] is False for option in options)
    await http_client.close_client()
    await http_client.close_client()
    assert len(pools) == 4
    assert all(pool.is_closed for pool in pools)


@pytest.mark.asyncio
async def test_one_pool_failure_does_not_skip_other_pool_or_log_details(client_factory, monkeypatch, caplog):
    _, pools, _ = client_factory
    with monkeypatch.context() as patch:
        patch.setattr(pools[0], 'close', Mock(side_effect=RuntimeError('synthetic-private-token')))
        await http_client.close_client()
        assert pools[1].is_closed
        assert 'HTTP connection pool cleanup failed' in caplog.text
        assert 'synthetic-private-token' not in caplog.text


@pytest.mark.asyncio
async def test_socket_cleanup_runs_off_the_event_loop(client_factory, monkeypatch):
    client, pools, _ = client_factory
    loop_thread = threading.get_ident()
    threads = []
    original_close = client.close

    def close():
        threads.append(threading.get_ident())
        original_close()

    monkeypatch.setattr(client, 'close', close)
    await http_client.close_client()
    assert len(threads) == 1 and threads[0] != loop_thread
    assert all(pool.is_closed for pool in pools)


def test_concurrent_requests_share_one_reopened_public_pool(client_factory):
    client, pools, _ = client_factory
    client.close()
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _: client.get('https://example.com/model').json(), range(16)))
    assert responses == [{'pool': 2}] * 16
    assert len(pools) == 3


@pytest.mark.parametrize('method', ['get', 'post', 'delete', 'stream'])
def test_reopening_does_not_bypass_ssrf_or_redirect_checks(client_factory, method):
    client, pools, _ = client_factory
    client.close()
    request = getattr(client, method)
    args = ['GET'] if method == 'stream' else []
    with pytest.raises(ValueError, match='Non-public'):
        request(*args, 'http://127.0.0.1/private')
    with pytest.raises(ValueError, match='redirects'):
        request(*args, 'https://example.com/redirect', follow_redirects=True)
    assert len(pools) == 2
