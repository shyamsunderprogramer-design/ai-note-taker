import asyncio
import json
from pathlib import Path
import pytest
from lib.sse_helpers import make_meta, make_content, make_done, make_error

@pytest.fixture
def race(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    for relative in ['core', 'modules/ai', 'modules/platform']:
        monkeypatch.syspath_prepend(str(root / relative))
    from routes import ai
    from modules.platform import cloud_providers as providers
    monkeypatch.setattr(ai, '_has_provider_key', lambda *args: True)
    monkeypatch.setattr(providers, 'PROVIDER_MODEL_MAP', {'groq-fast': ('groq', 'fast'), 'openai-slow': ('openai', 'slow')})
    def run(first, second):
        def factory(events, delay):
            async def stream(*args, **kwargs):
                for event in events:
                    await asyncio.sleep(delay)
                    yield event
            return stream
        monkeypatch.setattr(providers, 'get_stream_fn', lambda pk: factory(first if pk.startswith('groq') else second, .001 if pk.startswith('groq') else .015))
        async def collect():
            response = ai.stream_race('test', enabled='groq,openai')
            frames = [frame async for frame in response.body_iterator]
            return [json.loads(line[5:]) for frame in frames for line in frame.splitlines() if line.startswith('data:')]
        return asyncio.run(collect())
    return run

@pytest.mark.parametrize('first', [
    [make_meta('fast','groq'), make_done(1)],
    [make_meta('fast','groq'), make_error('bad key')],
    [make_meta('fast','groq'), make_content('  '), make_done(1)],
])
def test_metadata_empty_and_failed_streams_cannot_win(race, first):
    events = race(first, [make_meta('slow','openai'), make_content('Real answer'), make_content(' continues'), make_done(20)])
    assert events[0]['model'] == 'slow'
    assert ''.join(e.get('content','') for e in events) == 'Real answer continues'
    assert events[-1]['type'] == 'done'

def test_all_empty_is_an_error(race):
    events = race([make_meta('fast','groq'), make_done(1)], [make_meta('slow','openai'), make_done(20)])
    assert [e['type'] for e in events] == ['error']

def test_winner_failure_is_visible(race):
    events = race([make_meta('fast','groq'), make_content('Partial'), make_error('lost connection')], [make_content('Other')])
    assert events[-1]['type'] == 'error'
    assert not any(e['type'] == 'done' for e in events)

@pytest.mark.parametrize('frames, expected', [
    ([make_meta('model','ollama'), make_done(1)], 'error'),
    ([make_meta('model','ollama'), make_content('Valid answer'), make_done(1)], 'done'),
])
def test_explicit_stream_empty_is_not_success(race, monkeypatch, frames, expected):
    from routes import ai
    monkeypatch.setattr(ai, '_cache_ai_get', lambda *args: None)
    cached = []
    monkeypatch.setattr(ai, '_cache_ai_set', lambda *args: cached.append(args[-1]))
    async def stream(*args, **kwargs):
        for frame in frames:
            yield frame
    monkeypatch.setattr(ai, 'route_ai_stream', stream)
    async def collect():
        response = ai.stream_ai('test', provider='qwen3.5:9b')
        return [json.loads(line[5:]) async for frame in response.body_iterator for line in frame.splitlines() if line.startswith('data:')]
    events = asyncio.run(collect())
    assert events[-1]['type'] == expected
    assert cached == (['Valid answer'] if expected == 'done' else [])

@pytest.mark.parametrize('cloud_ok', [True, False])
def test_auto_uses_local_only_after_cloud_failure(monkeypatch, cloud_ok):
    root = Path(__file__).resolve().parents[1]
    for relative in ['core', 'modules/ai', 'modules/platform']:
        monkeypatch.syspath_prepend(str(root / relative))
    from routes import ai
    from modules.platform import cloud_providers as providers
    import ai_router
    calls = []
    monkeypatch.setattr(ai, '_has_provider_key', lambda provider, *a: provider == 'groq')
    monkeypatch.setattr(providers, 'PROVIDER_MODEL_MAP', {'groq-current': ('groq', 'current')})
    async def cloud(*a, **k):
        calls.append('cloud')
        yield make_meta('current', 'groq')
        await asyncio.sleep(.02)
        yield make_content('Cloud answer') if cloud_ok else make_error('quota')
        if cloud_ok:
            yield make_done(20)
    async def local(*a, **k):
        calls.append('local')
        yield make_meta('local', 'ollama')
        yield make_content('Local answer')
        yield make_done(1)
    monkeypatch.setattr(providers, 'get_stream_fn', lambda *a: cloud)
    monkeypatch.setattr(ai_router, 'ask_ollama_stream', local)
    async def collect():
        result = ai.stream_race('test', enabled='groq,ollama')
        return [frame async for frame in result.body_iterator]
    frames = asyncio.run(collect())
    assert calls == (['cloud'] if cloud_ok else ['cloud', 'local'])
    assert ('Cloud answer' if cloud_ok else 'Local answer') in ''.join(frames)
    assert not any('event: error' in frame for frame in frames)

@pytest.mark.parametrize('failure', [
    'Groq (HTTP 429): quota limit reached',
    'The answer reached its output limit and is incomplete',
    'Connection ended before the answer completed',
])
def test_hands_free_recovery_gap_after_partial_answer(race, failure):
    events = race(
        [make_meta('fast', 'groq'), make_content('Cedar is $1,400 over budget.'), make_error(failure)],
        [make_meta('slow', 'openai'), make_content('Maple is $300 under budget.'), make_done(20)],
    )
    assert ''.join(e.get('content', '') for e in events) == 'Cedar is $1,400 over budget.'
    assert events[-1]['type'] == 'error'
    assert not any(e['type'] == 'done' for e in events)
