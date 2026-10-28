"""Small live checks against an explicitly selected disposable ANT server."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import time
import uuid
import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8046')
parser.add_argument('--output', required=True)
parser.add_argument('--stream-model')
args = parser.parse_args()
results = []

def record(name, passed, detail):
    results.append({'name': name, 'passed': passed, 'detail': detail})
    Path(args.output).write_text(json.dumps({'updated': time.strftime('%Y-%m-%d %H:%M:%S'), 'server': args.url, 'checks': results}, indent=2))

with httpx.Client(base_url=args.url, timeout=10) as client:
    start = time.monotonic()
    r = client.get('/health')
    record('Server health', r.status_code == 200, f'HTTP {r.status_code}; {time.monotonic()-start:.3f}s')
    r = client.get('/health/ready')
    record('Core readiness', r.status_code == 200 and r.json().get('database_ready') is True, f'HTTP {r.status_code}; {r.text}')
    with ThreadPoolExecutor(max_workers=1) as pool:
        optional = pool.submit(client.get, '/health/modules')
        start = time.monotonic()
        live = client.get('/health')
        elapsed = time.monotonic() - start
        modules = optional.result()
    record('Liveness while optional modules are checked', live.status_code == 200 and elapsed < 1 and modules.status_code == 200, f'liveness={elapsed:.3f}s; modules HTTP {modules.status_code}')
    start = time.monotonic()
    r = client.get('/models/catalog')
    catalog = r.json().get('models', [])
    correct_cloud = all(m['provider'] == 'ollama-cloud' for m in catalog if m['id'].endswith((':cloud','-cloud')))
    record('Runtime model inventory', r.status_code == 200 and bool(catalog) and correct_cloud, f'HTTP {r.status_code}; {len(catalog)} entries; {time.monotonic()-start:.3f}s; cloud references classified separately')
    r = client.get('/mock-interview/practice-set', params={'num_questions':5})
    record('Five-question practice set', r.status_code == 200 and len(r.json().get('questions',[])) == 5, f'HTTP {r.status_code}; questions={len(r.json().get("questions",[]))}')
    r = client.get('/providers/byok/status')
    record('BYOK rejects missing credentials', r.status_code == 401, f'HTTP {r.status_code}')
    username = 'qa_' + uuid.uuid4().hex[:10]
    r = client.post('/auth/register', data={'username':username, 'email':username+'@example.com', 'password':'TestPass123!'})
    record('Disposable account registration', r.status_code in (200,201), f'HTTP {r.status_code}')
    r = client.post('/auth/login', data={'username':username, 'password':'TestPass123!'})
    r.raise_for_status()
    client.headers['Authorization'] = 'Bearer '+r.json()['access_token']
    r = client.get('/providers/byok/status')
    record('Authenticated BYOK status', r.status_code == 200 and 'providers' in r.json(), f'HTTP {r.status_code}')
    start = time.monotonic()
    r = client.get('/mock-interview/questions', params={'limit':10})
    body = r.json()
    record('Mock interview first page', r.status_code == 200 and len(body.get('questions',[])) == 10, f'HTTP {r.status_code}; {time.monotonic()-start:.3f}s; total={body.get("total")}')
    r = client.get('/mock-interview/questions', params={'limit':10,'offset':10})
    second = r.json()
    first_ids = {q['id'] for q in body.get('questions',[])}
    second_ids = {q['id'] for q in second.get('questions',[])}
    record('Stable distinct second page', r.status_code == 200 and len(second_ids)==10 and not first_ids & second_ids, f'HTTP {r.status_code}; {len(second_ids)} distinct questions')
    r = client.get('/mock-interview/search', params={'query':'design'})
    record('Mock interview search', r.status_code == 200 and 'questions' in r.json(), f'HTTP {r.status_code}; matches={r.json().get("total")}')
    if args.stream_model:
        start = time.monotonic()
        with client.stream('GET', '/stream', params={'q':'Reply with one short sentence confirming that streaming works.', 'provider':args.stream_model, 'mode':'fast', 'style':'concise'}, timeout=90) as response:
            payload = ''.join(response.iter_text())
            valid = response.status_code == 200 and 'event: done' in payload and 'event: error' not in payload and ('event: content' in payload or 'event: chunk' in payload)
            record('Local model answer stream', valid, f'HTTP {response.status_code}; {time.monotonic()-start:.3f}s; model={args.stream_model}; complete={"event: done" in payload}')
print(json.dumps(results, indent=2))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
