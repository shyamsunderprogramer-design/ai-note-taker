from types import SimpleNamespace
from lib import model_catalog


def test_inventory_distinguishes_cloud_references_and_local_capabilities(monkeypatch):
    model_catalog._metadata.clear()
    calls=[]
    def post(url,**kwargs):
        calls.append(kwargs['json']['model'])
        return SimpleNamespace(status_code=200,json=lambda:{'capabilities':['completion','vision'],'model_info':{'test.context_length':32768}})
    models=model_catalog.build_catalog([{'name':'custom:small','size':100},{'name':'remote:123b-cloud'},{'name':'remote:cloud'}],{},SimpleNamespace(post=post),'http://local')
    by_id={m['id']:m for m in models}
    assert calls==['custom:small']
    assert by_id['custom:small']['vision'] is True
    assert by_id['custom:small']['advertised_context_tokens']==32768
    assert by_id['custom:small']['configured'] is True
    for name in ['remote:123b-cloud','remote:cloud']:
        assert by_id[name]['provider']=='ollama-cloud'
        assert by_id[name]['configured'] is False
        assert by_id[name]['availability']=='unverified'
    assert by_id['openai-gpt-4o']['availability']=='unverified'


def test_metadata_failure_is_unknown_not_false_capability(monkeypatch):
    model_catalog._metadata.clear()
    def post(*a,**k): raise TimeoutError()
    models=model_catalog.build_catalog([{'name':'unknown:small'}],{'openai':True},SimpleNamespace(post=post),'http://local')
    local=next(m for m in models if m['id']=='unknown:small')
    assert local['vision'] is None
    assert local['advertised_context_tokens'] is None
    cloud=next(m for m in models if m['id']=='openai-gpt-4o')
    assert cloud['configured'] is True and cloud['availability']=='unverified'


def test_catalog_discovery_uses_short_local_deadline(monkeypatch):
    from routes import ollama
    monkeypatch.setattr(ollama, 'list_providers', lambda: {})
    timeouts = []
    def get(url, **kwargs):
        timeouts.append(kwargs['timeout'])
        raise TimeoutError('Ollama unavailable')
    monkeypatch.setattr(ollama.sync_client, 'get', get)
    result = ollama.model_catalog()
    assert timeouts and max(timeouts) <= 1
    assert result['models']
    assert all(not model['installed'] for model in result['models'])


def test_provider_discovery_does_not_serialize_key_server_timeouts(monkeypatch):
    import threading
    from routes import ollama
    barrier = threading.Barrier(8, timeout=2)
    def key(*args):
        barrier.wait()
        return False
    monkeypatch.setattr(ollama, '_has_provider_key', key)
    monkeypatch.setattr(ollama, '_probe_ollama', lambda: {'available': False})
    result = ollama.list_providers()
    assert result['ollama'] is False
    assert result['openai'] is False


def test_known_cloud_vision_is_not_filtered_out_as_unknown():
    models = model_catalog.build_catalog([], {'google': True, 'groq': True}, SimpleNamespace(), 'http://local')
    by_id = {m['id']: m for m in models}
    assert by_id['google-gemini-3-8-flash']['vision'] is True
    assert by_id['google-gemini-3-8-flash']['configured'] is True
    assert by_id['groq-gpt-oss-120b']['vision'] is False
    assert by_id['groq-gpt-oss-120b']['text'] is True
