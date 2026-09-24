"""Benchmark ANT's real local Ollama SSE helper and async adapter on synthetic notes."""
import argparse
import ast
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    ('Return three concise action items with owner and deadline. Use only these notes, '
     'and say unspecified for missing owners or deadlines. Notes: Please send the project summary '
     'by Friday. Maya will review the budget. Daniel will schedule the next meeting.',
     ['maya', 'daniel', 'friday', 'budget', 'summary']),
    ('Write a short interview answer using only these facts: I added a Redis cache. '
     'Latency dropped from 900 to 120 milliseconds. I paired with Priya to test the change. '
     'Do not invent outcomes or add other metrics.', ['redis', '120', 'priya']),
    ('Summarize decisions, blockers and next steps in under forty words. Notes: '
     'The release moved to Tuesday. Nina owns documentation. Tests are blocked pending '
     'staging access. Do not invent an owner for staging access.', ['tuesday', 'nina', 'staging']),
]
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))

async def run(args):
    import ai_router
    original_prompt = ai_router.build_prompt
    ai_router.build_prompt = lambda *a, **k: original_prompt(*a, **{**k, 'include_rag': False})
    tree = ast.parse(args.adapter.read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_patch_to_async_gen')
    namespace = {'asyncio': asyncio}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(args.adapter), 'exec'), namespace)
    stream = namespace['_patch_to_async_gen'](ai_router.ask_ollama_stream)
    samples = []
    for iteration in range(args.runs * len(CASES)):
        prompt, required = CASES[iteration // args.runs]
        lag = []
        finished = False
        async def heartbeat():
            while not finished:
                before = time.perf_counter()
                await asyncio.sleep(.02)
                lag.append(max(0, time.perf_counter()-before-.02))
        monitor = asyncio.create_task(heartbeat())
        await asyncio.sleep(0)
        start = time.perf_counter()
        first = None
        parts = []
        errors = []
        try:
            async for event in stream(prompt, mode='instant', model_name=args.model, style='concise', temperature=0):
                for line in event.splitlines():
                    if not line.startswith('data:'): continue
                    data = json.loads(line[5:])
                    if data.get('type') == 'error': errors.append(data)
                    content = data.get('content', '')
                    if content:
                        if first is None: first = time.perf_counter()-start
                        parts.append(content)
        finally:
            total = time.perf_counter()-start
            finished = True
            await monitor
        text = ''.join(parts)
        samples.append(dict(case=iteration // args.runs, run=iteration % args.runs+1, first_content_seconds=first, total_seconds=total,
                            max_event_loop_lag_seconds=max(lag, default=0), response=text, errors=errors,
                            required_facts_present=all(x in text.lower() for x in required),
                            final_answer_without_thinking='<think>' not in text.lower()))
    warm = samples[1:] or samples
    gates = dict(nonempty_responses=all(s['response'] and not s['errors'] for s in samples),
                 warm_first_content_under_2s=all(s['first_content_seconds'] is not None and s['first_content_seconds'] <= 2 for s in warm),
                 event_loop_lag_under_100ms=all(s['max_event_loop_lag_seconds'] <= .1 for s in samples),
                 factual_coverage=all(s['required_facts_present'] for s in samples),
                 final_answers=all(s['final_answer_without_thinking'] for s in samples))
    report = dict(model=args.model, cases=CASES, gates=gates, samples=samples,
                  limits='Local synthetic prompt, RAG disabled, first run may include model load. Fact matching is not a human quality evaluation. No HTTP frontend or auth included.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if all(gates.values()) else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='qwen3.5:9b')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--adapter', type=Path, default=ROOT / 'backend/core/main.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 1: parser.error('--runs must be positive')
    if 'cloud' in args.model: parser.error('Only local models are allowed')
    os.environ['RAG_ENABLED'] = 'false'
    raise SystemExit(asyncio.run(run(args)))
