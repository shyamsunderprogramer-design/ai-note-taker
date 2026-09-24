from types import SimpleNamespace
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def module_paths(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    for relative in ['core', 'modules/ai', 'modules/platform']:
        monkeypatch.syspath_prepend(str(root / relative))


def test_warmup_bounds_context(monkeypatch):
    from modules.ai import realtime_suggestions as live
    import httpx
    calls = []
    def post(url, **kwargs):
        calls.append(kwargs['json'])
        return SimpleNamespace(status_code=200)
    monkeypatch.setattr(httpx, 'post', post)
    assert live.warmup_live_model()['ok']
    assert calls[0]['options']['num_ctx'] == 2048
    assert calls[0]['prompt'] == ''


def test_nonstream_requests_bound_context_and_output(monkeypatch):
    import ai_router
    calls = []
    monkeypatch.setattr(ai_router, 'build_prompt', lambda prompt, *a: prompt)
    monkeypatch.setattr(ai_router, 'prepare_text_payload', lambda payload, *a: payload)
    def post(url, **kwargs):
        calls.append(kwargs['json'])
        return SimpleNamespace(status_code=200, json=lambda: {'response':'answer'})
    monkeypatch.setattr(ai_router.sync_client, 'post', post)
    ai_router.ask_ollama('question', model_name='qwen3.5:9b', style='concise')
    ai_router.ask_ollama('[Resume answer context] question', model_name='qwen3.5:9b', style='detailed')
    assert calls[0]['options']['num_ctx'] == 2048
    assert calls[0]['options']['num_predict'] == 300
    assert calls[1]['options']['num_ctx'] == 8192
    assert calls[1]['options']['num_predict'] == 2000

@pytest.mark.parametrize('style,minimum', [('concise',200), ('detailed',2000)])
def test_instant_answers_have_room_to_finish(monkeypatch, style, minimum):
    import ai_router
    from contextlib import contextmanager
    calls = []
    monkeypatch.setattr(ai_router, 'build_prompt', lambda *a, **k: 'question')
    monkeypatch.setattr(ai_router, 'prepare_text_payload', lambda payload, *a: payload)
    @contextmanager
    def stream(*args, **kwargs):
        calls.append(kwargs['json'])
        yield SimpleNamespace(status_code=200, iter_lines=lambda: iter(['{"response":"Done.","done":true}']))
    monkeypatch.setattr(ai_router.sync_client, 'stream', stream)
    list(ai_router.ask_ollama_stream('question',model_name='qwen3.5:9b',mode='instant',style=style))
    assert calls[0]['options']['num_predict'] >= minimum

@pytest.mark.parametrize('chunks,answer,error', [
    (['<thi', 'nk>Internal', ' work'], '', True),
    (['<think>Internal', '</thi', 'nk>', 'Final answer.'], 'Final answer.', False),
    ([' ', '\n'], ' \n', True),
])
def test_stream_exposes_only_final_answer(monkeypatch, chunks, answer, error):
    import ai_router
    import json
    from contextlib import contextmanager
    monkeypatch.setattr(ai_router, 'build_prompt', lambda *a, **k: 'question')
    monkeypatch.setattr(ai_router, 'prepare_text_payload', lambda payload, *a: payload)
    @contextmanager
    def stream(*a, **k):
        lines = [json.dumps({'response': chunk}) for chunk in chunks] + ['{"done":true}']
        yield SimpleNamespace(status_code=200, iter_lines=lambda: iter(lines))
    monkeypatch.setattr(ai_router.sync_client, 'stream', stream)
    events = [json.loads(line[5:]) for frame in ai_router.ask_ollama_stream('question')
              for line in frame.splitlines() if line.startswith('data:')]
    content = ''.join(item['content'] for item in events if item['type'] == 'chunk')
    assert content.strip() == answer.strip()
    assert any(item['type'] == 'error' for item in events) == error
    assert any(item['type'] == 'done' for item in events) != error

@pytest.mark.parametrize('lines,message', [
    ([{'response': 'Partial answer'}, {'done': True, 'done_reason': 'length'}], 'output limit'),
    ([{'response': 'Partial answer'}], 'connection ended'),
    ([{'response': 'Partial answer'}, {'error': 'runner stopped'}], 'failed during generation'),
])
def test_incomplete_generation_cannot_report_success(monkeypatch, lines, message):
    import ai_router
    import json
    from contextlib import contextmanager
    monkeypatch.setattr(ai_router, 'build_prompt', lambda *a, **k: 'question')
    monkeypatch.setattr(ai_router, 'prepare_text_payload', lambda payload, *a: payload)
    @contextmanager
    def stream(*a, **k):
        yield SimpleNamespace(status_code=200, iter_lines=lambda: iter(map(json.dumps, lines)))
    monkeypatch.setattr(ai_router.sync_client, 'stream', stream)
    events = [json.loads(line[5:]) for frame in ai_router.ask_ollama_stream('question')
              for line in frame.splitlines() if line.startswith('data:')]
    assert events[-1]['type'] == 'error'
    assert message in events[-1]['message']
    assert not any(event['type'] == 'done' for event in events)
