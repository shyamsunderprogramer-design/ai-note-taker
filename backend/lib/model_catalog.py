"""Runtime model inventory. Configured routes are not proof of provider availability."""
from concurrent.futures import ThreadPoolExecutor
import time

_metadata = {}

# Capability is independent of credential availability. Unknown must not hide
# known image-capable cloud routes from screenshot recovery.
_CLOUD_VISION = {'openai-gpt-4o', 'openai-gpt-4o-mini',
                 'google-gemini-3-8-flash', 'google-gemini-2-0-flash',
                 'anthropic-claude-sonnet-4-20250514', 'anthropic-claude-opus-4-20250514'}
_CLOUD_TEXT_ONLY = {'groq-gpt-oss-120b', 'groq-gpt-oss-20b'}


def local_details(name, client, base_url):
    cached = _metadata.get((base_url, name))
    if cached and time.monotonic() - cached[0] < 60:
        return cached[1]
    try:
        response = client.post(f'{base_url}/api/show', json={'model':name}, timeout=1, skip_ssrf_check=True)
        details = response.json() if response.status_code == 200 else {}
    except Exception:
        details = {}
    capabilities = details.get('capabilities')
    info = details.get('model_info', {})
    context = next((v for k,v in info.items() if k.endswith('.context_length') and isinstance(v,int) and v > 0), None)
    result = {'vision': 'vision' in capabilities if isinstance(capabilities,list) else None,
              'text': 'completion' in capabilities if isinstance(capabilities,list) else None,
              'advertised_context_tokens':context}
    _metadata[(base_url, name)] = (time.monotonic(), result)
    return result


def build_catalog(installed, configured, client, base_url):
    from modules.platform.cloud_providers import PROVIDER_MODEL_MAP, MODEL_DISPLAY_NAMES
    from lib.stream_recovery import provider_family
    models = {key:{'id':key,'name':MODEL_DISPLAY_NAMES.get(key,key), 'provider':provider,
                   'upstream_model':upstream,'installed':False,'configured':bool(configured.get(provider)),
                   'availability':'unverified','vision':True if key in _CLOUD_VISION else False if key in _CLOUD_TEXT_ONLY else None,'text':True,'advertised_context_tokens':None}
              for key,(provider,upstream) in PROVIDER_MODEL_MAP.items()}
    # Bound discovery work; never pull models or contact cloud inference endpoints.
    entries = [item for item in installed[:64] if isinstance(item,dict) and isinstance(item.get('name'),str)]
    local = [item for item in entries if provider_family(item['name']) != 'ollama-cloud'][:16]
    with ThreadPoolExecutor(max_workers=8) as pool:
        details = dict(zip([item['name'] for item in local], pool.map(lambda item:local_details(item['name'],client,base_url),local)))
    for item in entries:
        name = item['name']
        provider = 'ollama-cloud' if provider_family(name) == 'ollama-cloud' else 'ollama'
        models[name] = {'id':name,'name':name,'upstream_model':name,'provider':provider,'installed':True,
                        'configured':provider=='ollama' or bool(configured.get(provider)),
                        'availability':'installed' if provider=='ollama' else 'unverified',
                        'size':item.get('size'),**details.get(name,{'vision':None,'text':None,'advertised_context_tokens':None})}
    return list(models.values())
