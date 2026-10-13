"""Exercise real lifespan functions with isolated, mocked application resources."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'voice', 'database', 'http'])
async def test_shutdown_closes_each_resource_independently(monkeypatch, caplog, failure):
    from core import main
    from lib import http_client
    from modules.voice import local_clone_engine

    def closer(name):
        return AsyncMock(side_effect=RuntimeError('synthetic-private-token') if failure == name else None)

    close_voice, close_db, close_http = closer('voice'), closer('database'), closer('http')
    close_sync = Mock()
    monkeypatch.setattr(local_clone_engine, 'close_local_clone_engines', close_voice)
    monkeypatch.setattr(http_client, 'close_client', close_http)
    monkeypatch.setattr(http_client, 'sync_client', SimpleNamespace(close=close_sync))
    monkeypatch.setattr(main, 'close_database', close_db)
    monkeypatch.setattr(main, 'DATABASE_AVAILABLE', True)
    state = SimpleNamespace(use_autonomous=True)
    monkeypatch.setattr(main, '_state', state)
    await main.shutdown_event()
    close_voice.assert_awaited_once()
    close_db.assert_awaited_once()
    close_http.assert_awaited_once()
    close_sync.assert_not_called()  # The awaited hook owns both connection pools.
    assert not state.use_autonomous
    assert 'synthetic-private-token' not in caplog.text
    if failure:
        assert 'cleanup failed' in caplog.text


def test_uvicorn_owns_signal_handlers():
    tree = ast.parse((Path(__file__).parents[1] / 'core/main.py').read_text())
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and isinstance(node.func.value, ast.Name) and node.func.value.id == 'signal'
                   and node.func.attr == 'signal' for node in ast.walk(tree))


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'request', 'startup'])
async def test_application_lifespan_awaits_cleanup_even_on_failure(monkeypatch, failure):
    from core import main
    calls = []

    async def startup():
        calls.append('startup')
        if failure == 'startup':
            raise RuntimeError('synthetic startup failure')

    async def shutdown():
        calls.append('shutdown')

    monkeypatch.setattr(main, 'start_listener', startup)
    monkeypatch.setattr(main, 'shutdown_event', shutdown)

    async def run():
        async with main.application_lifespan(None):
            calls.append('request')
            if failure == 'request':
                raise RuntimeError('synthetic request failure')

    if failure:
        with pytest.raises(RuntimeError):
            await run()
    else:
        await run()
    assert calls == (['startup', 'shutdown'] if failure == 'startup'
                     else ['startup', 'request', 'shutdown'])
