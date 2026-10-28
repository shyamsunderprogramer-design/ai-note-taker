"""Real-provider comparison of prior buffering/high effort and faster spoken answers.

Run from the repository root. Uses configured Groq credentials without logging them.
Results measure the provider adapter and resume gate, not screenshot capture or UI.
"""
import asyncio
import json
from pathlib import Path
import sys
import time
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / 'backend/.env')
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))
from modules.platform import cloud_providers as cloud
from lib.async_stream import iterate_sync
from lib.resume_grounding import ResumeGrounding

build = cloud.build_prompt
cloud.build_prompt = lambda *a, **kw: build(*a, **{**kw, 'include_rag': False})
original_stream = cloud.sync_client.stream
baseline = False

def request(*args, **kwargs):
    if baseline:
        kwargs['json']['reasoning_effort'] = 'high'
    return original_stream(*args, **kwargs)
cloud.sync_client.stream = request

async def main():
    global baseline
    rows = []
    for question in ['What is a Kubernetes cluster and how would you configure it?',
                     'How would you manage on call rotations?']:
        prompt = ('[Resume answer context]\nResume data (JSON string): '
                  + json.dumps('Built Python APIs and collaborated with the operations team.')
                  + '\nQuestion: ' + question)
        for variant in ['before', 'after']:
            baseline = variant == 'before'
            async def create(query, history):
                async for frame in iterate_sync(cloud.ask_groq_stream(
                        query, mode='instant', style='spoken', temperature=.2)):
                    yield frame
            gate = ResumeGrounding(prompt)
            async def source():
                if baseline:
                    frames = [frame async for frame in create(prompt, [])]
                    text = ''.join(json.loads(line[5:]).get('content', '')
                                   for frame in frames for line in frame.splitlines()
                                   if line.startswith('data:'))
                    if gate.unsupported(text):
                        raise RuntimeError('Baseline failed grounding')
                    for frame in frames:
                        yield frame
                else:
                    async for frame in gate.stream(create, prompt, []):
                        yield frame
            started = time.perf_counter()
            first = None
            events = []
            async for frame in source():
                for line in frame.splitlines():
                    if line.startswith('data:'):
                        event = json.loads(line[5:])
                        events.append(event)
                        if event.get('type') == 'chunk' and event.get('content', '').strip() and first is None:
                            first = round((time.perf_counter() - started) * 1000)
            row = {'variant': variant, 'question': question, 'model': 'openai/gpt-oss-120b',
                   'first_visible_ms': first, 'complete_ms': round((time.perf_counter()-started)*1000),
                   'completed': bool(events and events[-1]['type'] == 'done'),
                   'answer': ''.join(e.get('content', '') for e in events),
                   'errors': [e.get('message') for e in events if e['type'] == 'error']}
            rows.append(row)
            print(json.dumps(row), flush=True)
    output = ROOT / 'qa/performance/results/2026-10-05-send-latency.json'
    output.write_text(json.dumps({'scope': 'Four sequential real Groq calls; includes network, prompt construction, inference and resume verification. Before emulates high effort and whole-answer buffering. Excludes desktop capture/OCR/provider discovery. Not a latency guarantee or exhaustive quality evaluation.', 'samples': rows}, indent=2))
    if not all(row['completed'] for row in rows):
        raise SystemExit(1)

asyncio.run(main())
