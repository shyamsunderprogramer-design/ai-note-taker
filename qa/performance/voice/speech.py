"""Local synthetic speech benchmark. Uses cached models; never downloads or calls providers."""
import argparse
import importlib.util
import json
import math
import os
import platform
import re
import statistics
import subprocess
import time
from pathlib import Path

REFERENCES = [
    'Please send the project summary by Friday. Maya will review the budget, and Daniel will schedule the next meeting.',
    'Tell me about a time you solved a difficult problem. What did you change, and how did you measure the result?',
    'The service handles forty requests per second. We need to reduce response time and add a test before the next release.',
]

def word_error_rate(reference, actual):
    ref = re.findall(r"\w+", reference.lower())
    hyp = re.findall(r"\w+", actual.lower())
    row = list(range(len(hyp) + 1))
    for i, word in enumerate(ref, 1):
        new = [i]
        for j, other in enumerate(hyp, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j-1] + (word != other)))
        row = new
    return row[-1] / max(1, len(ref))

def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path('/tmp/ant-product-benchmark'))
    parser.add_argument('--module', type=Path, default=Path(__file__).resolve().parents[3] / 'backend/modules/voice/whisper_handler.py')
    parser.add_argument('--model', choices=['small', 'base'], default='small')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--generate', action='store_true', help='Generate macOS Samantha speech fixtures')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 1: parser.error('--runs must be positive')
    os.environ['HF_HUB_OFFLINE'] = '1'
    args.fixtures.mkdir(parents=True, exist_ok=True)
    if args.generate:
        for i, reference in enumerate(REFERENCES):
            subprocess.run(['say', '-v', 'Samantha', '-r', '170', '-o', str(args.fixtures / f'speech-{i}.aiff'), reference], check=True)
    import soundfile as sf
    import numpy as np
    sf.write(args.fixtures / 'silence.wav', np.zeros(16000 * 3), 16000)
    spec = importlib.util.spec_from_file_location('speech_under_test', args.module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.select_model = lambda *a, **k: args.model
    started = time.perf_counter()
    module.get_model(streaming=True)
    load_seconds = time.perf_counter() - started
    module.model_ready.set()
    rows = []
    for i, reference in enumerate(REFERENCES):
        path = args.fixtures / f'speech-{i}.aiff'
        info = sf.info(path)
        if info.duration <= 0:
            raise RuntimeError(f"Speech fixture is empty: {path}. Generation did not produce audio.")
        for run in range(args.runs):
            started = time.perf_counter()
            result = module.transcribe_audio(str(path), fast=True)
            elapsed = time.perf_counter() - started
            transcript = result.get('text', '') if isinstance(result, dict) else result or ''
            rows.append(dict(clip=i, run=run+1, sample_rate=info.samplerate, duration_seconds=info.duration,
                             elapsed_seconds=elapsed, real_time_factor=elapsed/info.duration,
                             reference=reference, transcript=transcript, wer=word_error_rate(reference, transcript)))
    silence = module.transcribe_audio(str(args.fixtures / 'silence.wav'), fast=True)
    silence_text = silence.get('text', '') if isinstance(silence, dict) else silence or ''
    metrics = dict(p50_seconds=statistics.median(r['elapsed_seconds'] for r in rows),
                   p95_seconds=percentile([r['elapsed_seconds'] for r in rows], .95),
                   p95_real_time_factor=percentile([r['real_time_factor'] for r in rows], .95),
                   mean_wer=statistics.mean(r['wer'] for r in rows), silence_transcript=silence_text)
    gates = dict(synthetic_wer=metrics['mean_wer'] <= .15,
                 faster_than_half_real_time=metrics['p95_real_time_factor'] <= .5,
                 silence_no_hallucination=not silence_text.strip())
    report = dict(model=args.model, platform=platform.platform(), python=platform.python_version(),
                  model_load_seconds=load_seconds, fixture='macOS Samantha 170 wpm; 3 synthetic clean-English clips',
                  limits='Not representative human speech; no microphone, network, streaming endpoint, or AI response measured.',
                  gates=gates, metrics=metrics, samples=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'}, indent=2))
    return 0 if all(gates.values()) else 1

if __name__ == '__main__':
    raise SystemExit(main())
