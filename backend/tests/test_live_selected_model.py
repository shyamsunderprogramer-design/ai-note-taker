import sys
from pathlib import Path
import pytest


@pytest.mark.asyncio
async def test_live_selection_passed_unchanged_and_errors_not_hidden(monkeypatch):
    for relative in ['core', 'modules/ai']:
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / relative))
    import ai_router
    from lib.live_model_stream import collect_selected_model
    seen = []
    async def route(prompt, **kwargs):
        seen.append(kwargs['provider'])
        yield 'data: {"type":"content","content":"selected answer"}\n\n'
    monkeypatch.setattr(ai_router, 'route_ai_stream', route)
    assert await collect_selected_model('question', 'openai-gpt-4o') == 'selected answer'
    assert seen == ['openai-gpt-4o']
    async def failed(*args, **kwargs):
        yield 'data: {"type":"error","message":"provider unavailable"}\n\n'
    monkeypatch.setattr(ai_router, 'route_ai_stream', failed)
    with pytest.raises(RuntimeError, match='provider unavailable'):
        await collect_selected_model('question', 'openai-gpt-4o')


@pytest.mark.parametrize('selected,expected', [('openai-gpt-4o','gpt-4o'), ('test-vision:1b','test-vision:1b')])
def test_screenshot_request_keeps_selected_model(monkeypatch, selected, expected):
    for relative in ['core', 'modules/ai']:
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / relative))
    import ai_router
    from modules.platform import cloud_providers
    from routes.ai import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    seen = []
    async def stream(*args, **kwargs):
        seen.append(kwargs.get('model', kwargs.get('model_name')))
        yield 'data: {"type":"content","content":"answer"}\n\n'
    monkeypatch.setattr(cloud_providers, 'get_vision_stream_fn', lambda provider: stream)
    monkeypatch.setattr(ai_router, 'ask_ollama_vision_stream', stream)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post('/ask-with-image', data={'query':'question','provider':selected,'image_b64':'synthetic'})
    assert response.status_code == 200
    assert seen == [expected]

@pytest.mark.asyncio
async def test_auto_continues_after_cloud_error_before_answer(monkeypatch):
    for relative in ['core', 'modules/ai', 'modules/platform']:
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / relative))
    import ai_router
    from modules.platform import cloud_providers as cloud
    from lib.sse_helpers import make_error, make_meta, make_content, make_done
    calls = []
    monkeypatch.setattr(ai_router, '_has_provider_key_fast', lambda *a: True)
    async def bad(*a, **k):
        calls.append('bad')
        yield make_meta('unavailable', 'groq')
        yield make_error('quota')
    async def good(*a, **k):
        calls.append('good')
        yield make_meta('available', 'google')
        yield make_content('Cloud answer')
        yield make_done(1)
    monkeypatch.setattr(cloud, 'get_stream_fn', lambda candidate: bad if candidate.startswith('groq-') else good)
    frames = [frame async for frame in ai_router.route_ai_stream('question', provider='auto')]
    assert calls == ['bad', 'good']
    assert 'Cloud answer' in ''.join(frames)
    assert 'quota' not in ''.join(frames)
    assert 'unavailable' not in ''.join(frames)


@pytest.mark.asyncio
async def test_auto_does_not_replace_a_partial_answer_on_failure(monkeypatch):
    for relative in ['core', 'modules/ai', 'modules/platform']:
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / relative))
    import ai_router
    from modules.platform import cloud_providers as cloud
    from lib.sse_helpers import make_error, make_content
    calls = []
    monkeypatch.setattr(ai_router, '_has_provider_key_fast', lambda *a: True)
    async def partial(*a, **k):
        calls.append(k['model'])
        yield make_content('Partial answer')
        yield make_error('disconnected')
    monkeypatch.setattr(cloud, 'get_stream_fn', lambda *a: partial)
    frames = [frame async for frame in ai_router.route_ai_stream('question', provider='auto')]
    assert len(calls) == 1
    assert 'Partial answer' in ''.join(frames)
    assert 'event: error' in frames[-1]
