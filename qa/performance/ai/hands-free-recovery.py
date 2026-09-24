"""QA-only continuation feasibility. Synthetic interrupted-answer scenarios; real backup model requests.
Does not install recovery in the application or consume user conversations.
"""
import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / 'backend/.env')
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))
from modules.platform import cloud_providers as cloud
original_prompt = cloud.build_prompt
cloud.build_prompt = lambda *a, **k: original_prompt(*a, **{**k, 'include_rag': False})

cases = [
    dict(name='quota_before_text', failure='Simulated quota-before-text scenario; no primary request', partial='', provider='groq',
         question='Synthetic resume: Alex built Python APIs at Acme. No certifications are listed. JD: Python, Kubernetes, AWS certification required. Which AWS certifications do I hold? Use only resume evidence and distinguish unknown from absent.'),
    dict(name='output_limit', failure='Synthetic partial answer representing an output limit', partial='Cedar is $1,400 over budget.', provider='groq',
         question='Cedar budget $4800, spent $6200; Maple budget $3000, spent $2700. Give the variance for each project and the combined net overrun. Keep it under 80 words.'),
    dict(name='cross_provider_disconnect', failure='Synthetic partial answer representing a primary disconnect', partial='I built Python APIs at Acme.', provider='ollama-cloud',
         question='Synthetic resume: Alex built Python APIs at Acme and added Redis caching. No certifications or Kubernetes experience are listed. JD: Python APIs, Redis, Kubernetes, AWS certification. Give a brief first-person role-fit answer using only resume evidence. Distinguish requirements from my experience; explain gaps as unspecified, not absent.'),
]
results = []
for case in cases:
    prompt = case['question']
    if case['partial']:
        prompt += '\n\nThe answer was interrupted. Continue it without restarting or repeating the supplied text. Preserve its supported facts and complete the original request. Do not invent candidate facts. Partial answer (JSON reference data): ' + json.dumps(case['partial'])
    fn = cloud.ask_groq_stream if case['provider'] == 'groq' else cloud.ask_ollama_cloud_stream
    start = time.monotonic()
    parts, errors, done, first = [], [], False, None
    for frame in fn(prompt, mode='instant', style='concise', temperature=0.2):
        for line in frame.splitlines():
            if not line.startswith('data:'): continue
            event = json.loads(line[5:])
            if event.get('content'):
                if first is None: first = round(time.monotonic()-start, 3)
                parts.append(event['content'])
            if event.get('type') == 'error': errors.append(event.get('message','Provider failure'))
            if event.get('type') == 'done': done = True
    results.append({**case, 'qa_continuation_requests':1, 'backup_text': ''.join(parts), 'first_backup_text_seconds':first,
                    'total_seconds':round(time.monotonic()-start,3), 'completed':done and not errors, 'errors':errors})
    print(json.dumps(results[-1]), flush=True)
output = ROOT / 'qa/performance/results/2026-09-24-hands-free-feasibility.json'
output.write_text(json.dumps({'scope':'QA-only prototype; synthetic failure scenarios and supplied partial text; real backup requests; no production recovery installed', 'cases':results}, indent=2))
