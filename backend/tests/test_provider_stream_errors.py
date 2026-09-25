import json
from contextlib import contextmanager
from pathlib import Path
import sys

import httpx
import pytest
from lib.provider_stream import chat_content, check_provider_status, ProviderResponseError

for part in ['core', 'modules/ai', 'modules/platform']:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / part))


def response(events, status=200):
    return httpx.Response(status, content='\n\n'.join(
        'data: ' + (event if isinstance(event, str) else json.dumps(event)) for event in events).encode())


@pytest.mark.parametrize('status', [400, 401, 402, 403, 404, 410, 429, 500])
def test_http_errors_do_not_expose_provider_response(status):
    resp = httpx.Response(status, json={'error': {'message': 'api-key-secret'}})
    with pytest.raises(ProviderResponseError) as exc:
        check_provider_status(resp, 'Groq')
    assert str(status) in str(exc.value)
    assert 'api-key-secret' not in str(exc.value)


def test_reasoning_and_usage_do_not_become_answers():
    resp = response([
        {'choices': [{'delta': {'reasoning': 'private analysis'}}]},
        {'choices': [{'delta': {'content': 'Visible answer'}}]},
        {'choices': [], 'usage': {'total_tokens': 50}},
        {'choices': [{'delta': {}, 'finish_reason': 'stop'}]}, '[DONE]'])
    assert ''.join(chat_content(resp, 'Groq')) == 'Visible answer'


@pytest.mark.parametrize('events', [
    [{'choices': [{'delta': {'content': 'Partial'}}]}],
    [{'choices': [{'delta': {'content': 'Partial'}, 'finish_reason': 'length'}]}, '[DONE]'],
    [{'choices': [{'delta': {}, 'finish_reason': 'content_filter'}]}, '[DONE]'],
    [{'error': {'message': 'provider-secret'}}],
    ['[DONE]'],
    ['invalid JSON'],
])
def test_incomplete_answers_are_errors(events):
    with pytest.raises(ProviderResponseError) as exc:
        list(chat_content(response(events), 'Groq'))
    assert 'provider-secret' not in str(exc.value)


@pytest.mark.parametrize('provider', ['groq', 'google', 'openai'])
def test_cloud_adapter_auth_failure_is_not_a_success(monkeypatch, provider):
    from modules.platform import cloud_providers as cloud
    monkeypatch.setattr(cloud, 'build_prompt', lambda *a, **k: 'question')
    resp = response([], 401)
    @contextmanager
    def stream(*a, **k):
        yield resp
    monkeypatch.setattr(cloud.sync_client, 'stream', stream)
    monkeypatch.setattr(cloud, 'get_groq_key', lambda: 'fake-key')
    monkeypatch.setattr(cloud, 'get_google_key', lambda: 'fake-key')
    monkeypatch.setattr(cloud, 'ask_gpt', lambda *a, **k: resp)
    fn = {'groq': cloud.ask_groq_stream, 'google': cloud.ask_gemini_stream, 'openai': cloud.ask_gpt_stream}[provider]
    frames = list(fn('question'))
    assert len(frames) == 1 and 'event: error' in frames[0]
    assert '401' in frames[0]
    assert 'fake-key' not in ''.join(frames)


def test_google_sends_key_in_header_and_preserves_all_public_parts(monkeypatch):
    from modules.platform import cloud_providers as cloud
    calls = []
    monkeypatch.setattr(cloud, 'build_prompt', lambda *a, **k: 'question')
    monkeypatch.setattr(cloud, 'get_google_key', lambda: 'fake-key')
    @contextmanager
    def stream(method, url, **kwargs):
        calls.append((url, kwargs))
        yield response([{'candidates': [{'content': {'parts': [
            {'text': 'private analysis', 'thought': True}, {'text': 'First '}, {'text': 'second.'}
        ]}, 'finishReason': 'STOP'}]}])
    monkeypatch.setattr(cloud.sync_client, 'stream', stream)
    frames = list(cloud.ask_gemini_stream('question'))
    assert calls[0][1]['headers']['x-goog-api-key'] == 'fake-key'
    assert 'fake-key' not in calls[0][0]
    assert 'private analysis' not in ''.join(frames)
    assert 'First ' in ''.join(frames) and 'second.' in ''.join(frames)
    assert 'event: done' in frames[-1]


@pytest.mark.parametrize('ending,success', [
    ({'done': True, 'done_reason': 'stop'}, True),
    ({'done': True, 'done_reason': 'length'}, False),
    ({'error': 'secret-provider-detail'}, False),
    ({'done': False}, False),
])
def test_ollama_cloud_requires_completion_and_uses_grounded_prompt(monkeypatch, ending, success):
    from modules.platform import cloud_providers as cloud
    calls = []
    monkeypatch.setattr(cloud, 'build_prompt', lambda *a, **k: 'grounded prompt with history')
    monkeypatch.setattr(cloud, 'get_ollama_cloud_key', lambda: 'fake-key')
    @contextmanager
    def stream(method, url, **kwargs):
        calls.append(kwargs)
        yield httpx.Response(200, content='\n'.join(map(json.dumps, [
            {'message': {'content': 'Visible answer', 'thinking': 'private'}}, ending])))
    monkeypatch.setattr(cloud.sync_client, 'stream', stream)
    frames = ''.join(cloud.ask_ollama_cloud_stream('question', model='minimax-m3:cloud'))
    assert calls[0]['json']['model'] == 'minimax-m3'
    assert calls[0]['json']['messages'][0]['content'] == 'grounded prompt with history'
    assert ('event: done' in frames) == success
    assert ('event: error' in frames) != success
    assert 'secret-provider-detail' not in frames and 'private' not in frames


def test_rate_limit_carries_retry_after_without_echoing_error_body():
    resp = httpx.Response(429, headers={'Retry-After':'90'}, json={'error':'secret'})
    with pytest.raises(ProviderResponseError) as caught:
        check_provider_status(resp,'Groq')
    assert caught.value.code == 'rate_limit'
    assert caught.value.retry_after == 90
    assert 'secret' not in str(caught.value)


def test_context_window_is_classified_without_echoing_prompt():
    resp = httpx.Response(400,json={'error':{'code':'context_length_exceeded','message':'secret prompt'}})
    with pytest.raises(ProviderResponseError) as caught:
        check_provider_status(resp,'Groq')
    assert caught.value.code == 'context_limit'
    assert 'secret' not in str(caught.value)


def test_mid_stream_quota_has_machine_readable_code():
    resp = response([{'error':{'code':'rate_limit_exceeded','message':'secret'}}])
    with pytest.raises(ProviderResponseError) as caught:
        list(chat_content(resp,'Groq'))
    assert caught.value.code == 'rate_limit'
    assert 'secret' not in str(caught.value)

@pytest.mark.parametrize('adapter,key_getter,protocol', [
    ('ask_grok_stream','get_xai_key','chat'),
    ('ask_deepseek_stream','get_deepseek_key','chat'),
    ('ask_perplexity_stream','get_perplexity_key','chat'),
    ('ask_claude_stream','get_anthropic_key','anthropic'),
    ('ask_gpt_vision_stream','get_openai_key','chat'),
    ('ask_groq_vision_stream','get_groq_key','chat'),
    ('ask_claude_vision_stream','get_anthropic_key','anthropic'),
    ('ask_gemini_vision_stream','get_google_key','gemini'),
])
@pytest.mark.parametrize('ending', ['complete','limit','eof','quota'])
def test_text_and_vision_adapters_report_terminal_state(monkeypatch,adapter,key_getter,protocol,ending):
    from modules.platform import cloud_providers as cloud
    monkeypatch.setattr(cloud,key_getter,lambda:'fake-key')
    monkeypatch.setattr(cloud,'build_prompt',lambda *a,**k:'question')
    if protocol=='chat':
        events=[{'choices':[{'delta':{'content':'Answer'}}]}]
        if ending not in ('eof','quota'): events += [{'choices':[{'delta':{},'finish_reason':'length' if ending=='limit' else 'stop'}]},'[DONE]']
    elif protocol=='anthropic':
        events=[{'type':'content_block_delta','delta':{'type':'text_delta','text':'Answer'}}]
        if ending not in ('eof','quota'): events += [{'type':'message_delta','delta':{'stop_reason':'max_tokens' if ending=='limit' else 'end_turn'}},{'type':'message_stop'}]
    else:
        events=[{'candidates':[{'content':{'parts':[{'text':'Answer'}]}}]}]
        if ending not in ('eof','quota'): events += [{'candidates':[{'finishReason':'MAX_TOKENS' if ending=='limit' else 'STOP'}]}]
    @contextmanager
    def stream(*a,**k): yield response(events,429 if ending=='quota' else 200)
    monkeypatch.setattr(cloud.sync_client,'stream',stream)
    frames=list(getattr(cloud,adapter)('question'))
    data=[json.loads(line[5:]) for frame in frames for line in frame.splitlines() if line.startswith('data:')]
    assert data[-1]['type']==('done' if ending=='complete' else 'error')
    if ending=='limit': assert data[-1]['code']=='output_limit'
    if ending=='quota': assert data[-1]['code']=='rate_limit'
    if ending!='complete': assert not any(e['type']=='done' for e in data)
