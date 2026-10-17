"""Provider discovery keeps its cache semantics without importing the ASGI app."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lib import provider_status as status


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(status, '_provider_key_cache', {})
    monkeypatch.delenv('ANT_QA_PROVIDER_KEY', raising=False)


def test_environment_key_does_not_call_the_key_server(monkeypatch):
    request = Mock(side_effect=AssertionError('environment keys need no request'))
    monkeypatch.setattr(status, 'sync_client', SimpleNamespace(post=request))
    monkeypatch.setenv('ANT_QA_PROVIDER_KEY', 'synthetic-private-key')
    assert status.has_provider_key('qa', 'ANT_QA_PROVIDER_KEY') is True
    assert status._provider_key_cache['qa'][0] is True
    request.assert_not_called()


def test_per_provider_expiration_uses_monotonic_time(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(status.time, 'monotonic', lambda: clock[0])
    request = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {'apiKey': 'synthetic-key'}))
    monkeypatch.setattr(status, 'sync_client', SimpleNamespace(post=request))
    assert status.has_provider_key('first', 'ANT_QA_PROVIDER_KEY')
    clock[0] = 105.0
    assert status.has_provider_key('second', 'ANT_QA_PROVIDER_KEY')
    assert status.has_provider_key('first', 'ANT_QA_PROVIDER_KEY')
    assert request.call_count == 2
    clock[0] = 111.0
    assert status.has_provider_key('first', 'ANT_QA_PROVIDER_KEY')
    assert status.has_provider_key('second', 'ANT_QA_PROVIDER_KEY')
    assert request.call_count == 3


@pytest.mark.parametrize('reply', [None, 403, 200])
def test_missing_key_and_server_failure_do_not_report_availability(monkeypatch, reply):
    request = Mock(side_effect=RuntimeError('private-server-details') if reply is None else None,
                   return_value=SimpleNamespace(status_code=reply, json=lambda: {}))
    monkeypatch.setattr(status, 'sync_client', SimpleNamespace(post=request))
    assert status.has_provider_key('qa', 'ANT_QA_PROVIDER_KEY') is False
    assert status.has_provider_key('qa', 'ANT_QA_PROVIDER_KEY') is False
    request.assert_called_once()
    assert request.call_args.args == ('http://127.0.0.1:18000/get-key',)
    assert request.call_args.kwargs['timeout'] == 2


def test_batch_preserves_each_provider_result(monkeypatch):
    monkeypatch.setattr(status, 'has_provider_key', lambda provider, env: provider == 'ready')
    assert status.batch_check_provider_keys([]) == {}
    assert status.batch_check_provider_keys([('ready', 'KEY_A'), ('missing', 'KEY_B')]) == {
        'ready': True, 'missing': False,
    }


def test_cloud_prompt_uses_current_builder(monkeypatch):
    import ai_router
    from modules.platform import cloud_providers
    builder = Mock(return_value='updated prompt with current session context')
    monkeypatch.setattr(ai_router, 'build_prompt', builder)
    assert cloud_providers.build_prompt('follow-up', include_rag=False) == builder.return_value
    builder.assert_called_once_with('follow-up', include_rag=False)


@pytest.mark.asyncio
async def test_vision_key_lookup_runs_outside_the_audio_event_loop(monkeypatch):
    import threading
    import ai_router
    import httpx
    from fastapi import FastAPI
    from routes import ai

    event_thread = threading.get_ident()
    lookup_threads = []

    def lookup(providers):
        lookup_threads.append(threading.get_ident())
        return {provider: False for provider, _ in providers}

    monkeypatch.setattr(status, 'batch_check_provider_keys', lookup)
    monkeypatch.setattr(ai_router, '_get_vision_model', lambda: None)
    app = FastAPI()
    app.include_router(ai.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        response = await client.post('/ask-with-image', data={
            'query': 'Explain this synthetic screenshot', 'provider': 'auto',
            'image_b64': 'c3ludGhldGlj', 'enabled': 'groq',
        })
    assert response.status_code == 200
    assert lookup_threads and all(t != event_thread for t in lookup_threads)
    assert 'No vision-capable model found' in response.text
