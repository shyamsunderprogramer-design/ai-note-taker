"""Small, real local-model comparison. Human review of answers is required."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
for relative in ['backend','backend/core','backend/modules/ai','backend/modules/platform']:
    sys.path.insert(0,str(ROOT / relative))
import ai_router
original = ai_router.build_prompt
ai_router.build_prompt = lambda *a, **k: original(*a, **{**k,'include_rag':False})
CASES = [
    ('missing_fact', '[Resume answer context] Resume: Jordan built Python APIs at Acme and added Redis caching. No certifications are listed. Which AWS certifications do I hold and when did I earn them? Use only the resume for personal facts. Unlisted does not mean absent.'),
    ('meeting', 'Please send the project summary by Friday. Maya will review the budget, and Daniel will schedule the next meeting. Summarize these action items with each owner and deadline. Mark missing details unspecified. Do not invent dependencies between tasks.'),
    ('technical', 'Explain how readiness probes, liveness probes, and memory limits affect a Kubernetes pod. Distinguish removal from traffic from container restarts. Which component enforces the memory limit?'),
]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('models', nargs='*', default=['qwen3.5:9b','lfm2.5:latest','gemma4:e4b'])
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--reasoning-experiment', action='store_true',
                    help='QA only: compare the same Qwen model with its thinking prefix enabled')
parser.add_argument('--list-cloud-models', action='store_true', help='Check configured cloud catalogs without printing credentials')
parser.add_argument('--cases', type=Path, help='Additional synthetic [name, prompt] pairs for held-out checks')
parser.add_argument('--interval', type=float, default=0, help='Seconds between requests to respect provider rate limits')
parser.add_argument('--only', help='Comma-separated case names for focused provider checks')
args = parser.parse_args()
output = args.output
if args.list_cloud_models:
    import httpx
    from concurrent.futures import ThreadPoolExecutor
    endpoints = [
        ('openai', 'OPENAI_API_KEY', 'https://api.openai.com/v1/models'),
        ('google', 'GOOGLE_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/models'),
        ('groq', 'GROQ_API_KEY', 'https://api.groq.com/openai/v1/models'),
    ]
    def catalog(item):
        provider, env, url = item
        key = os.getenv(env, '').strip()
        if not key:
            return {'provider': provider, 'configured': False}
        headers = {'x-goog-api-key': key} if provider == 'google' else {'Authorization': 'Bearer ' + key}
        try:
            response = httpx.get(url, headers=headers, timeout=20)
            result = {'provider': provider, 'configured': True, 'status': response.status_code}
            if response.status_code == 200:
                data = response.json()
                result['models'] = sorted(model.get('id', model.get('name', '')) for model in data.get('data', data.get('models', [])))
            return result
        except Exception as exc:
            return {'provider': provider, 'configured': True, 'error': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=3) as executor:
        catalogs = list(executor.map(catalog, endpoints))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalogs, indent=2))
    print(json.dumps(catalogs, indent=2))
    raise SystemExit(0 if all(item.get('status') == 200 for item in catalogs if item['configured']) else 1)
if args.reasoning_experiment:
    prepare = ai_router.prepare_text_payload
    base_filter = ai_router.PublicAnswerFilter
    def reasoning_payload(payload, *a, **k):
        result = prepare(payload, *a, **k)
        if not result.get('raw') or not result['model'].startswith('qwen3.5:'):
            raise ValueError('This experiment requires the known raw-only Qwen template')
        result['prompt'] = result['prompt'].removesuffix('<think>\n\n</think>\n\n') + '<think>\n'
        result['options'] = {**result['options'], 'num_predict': 1536, 'num_ctx': 4096}
        return result
    class ReasoningFilter(base_filter):
        def __init__(self):
            super().__init__()
            self.feed('<think>')
    ai_router.prepare_text_payload = reasoning_payload
    ai_router.PublicAnswerFilter = ReasoningFilter
CASES += [
    ('meeting_status', 'Transcript: Priya proposed moving the release to Monday. Omar said he needs test results before agreeing. No date was decided. Lee already sent the draft. Extract the decisions and action items. Do not turn proposals into decisions.'),
    ('meeting_owners', 'Transcript: Elena will send the invoice on Tuesday. Marcus will check the contract; no due date was given. The launch checklist needs updating by Thursday, but nobody volunteered. List each action with its owner and deadline.'),
    ('technical_restart', 'A container in a Kubernetes pod is OOMKilled. Does a liveness probe need to fail for it to restart? Explain what determines whether it restarts.'),
]
if args.cases:
    CASES.extend(json.loads(args.cases.read_text()))
if args.only:
    wanted = set(args.only.split(','))
    if wanted - {name for name, _ in CASES}:
        parser.error('Unknown case name in --only')
    CASES = [(name, prompt) for name, prompt in CASES if name in wanted]
results=[]
from modules.platform import cloud_providers
cloud_providers.build_prompt = ai_router.build_prompt
for model in args.models:
    for name,prompt in CASES:
        if results and args.interval:
            time.sleep(args.interval)
        start=time.perf_counter(); first=None; parts=[]; errors=[]
        try:
            if model in cloud_providers.PROVIDER_MODEL_MAP:
                provider, remote_model = cloud_providers.PROVIDER_MODEL_MAP[model]
                stream = cloud_providers.get_stream_fn(model)(prompt, model=remote_model, mode='adaptive', style='concise', temperature=0)
            else:
                stream = ai_router.ask_ollama_stream(prompt,mode='adaptive',model_name=model,style='concise',temperature=0)
            for frame in stream:
                for line in frame.splitlines():
                    if not line.startswith('data:'): continue
                    item=json.loads(line[5:])
                    if item.get('type')=='error': errors.append(item.get('message'))
                    if item.get('type')=='chunk' and item.get('content'):
                        if first is None and item['content'].strip():first=time.perf_counter()-start
                        parts.append(item['content'])
        except Exception as exc: errors.append(type(exc).__name__)
        row={'model':model,'case':name,'first_seconds':first,'total_seconds':time.perf_counter()-start,'answer':''.join(parts),'errors':errors}
        results.append(row)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({'conditions':'Production provider adapter; temperature 0; concise; RAG disabled; first sample may include loading. Not a desktop or exhaustive accuracy test.', 'reasoning_experiment':args.reasoning_experiment, 'samples':results},indent=2))
        print(json.dumps(row),flush=True)

# Generation failures must fail the command; semantic accuracy still needs review.
raise SystemExit(1 if any(row['errors'] or not row['answer'].strip() for row in results) else 0)
