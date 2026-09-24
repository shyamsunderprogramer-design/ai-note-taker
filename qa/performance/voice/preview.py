"""Compare phrase previews with a complete recording using cached Whisper."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from faster_whisper.audio import decode_audio

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from modules.voice.whisper_handler import BrowserTranscriber, get_model, model_ready

spec = importlib.util.spec_from_file_location('speech_benchmark', Path(__file__).with_name('speech.py'))
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--audio', type=Path, default=Path('/tmp/ant-product-benchmark/speech-0.aiff'))
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
os.environ['HF_HUB_OFFLINE'] = '1'
get_model(streaming=True)
model_ready.set()
audio = decode_audio(str(args.audio), sampling_rate=16000)
transcriber = BrowserTranscriber()
previews = []
transcriber.add_callback(previews.append)
transcriber.start_worker()
started = time.perf_counter()
try:
    # Feed packet-sized chunks; queue stays bounded. This measures decode cost,
    # not wall-clock latency while someone speaks.
    for start in range(0, len(audio), 1600):
        transcriber.add_chunk(audio[start:start+1600])
    text = transcriber.get_final()
finally:
    transcriber.stop()
result = {'fixture': 'macOS Samantha synthetic clean English; meeting actions',
          'limits': 'One synthetic fixture, accelerated packet delivery; not human speech or microphone acceptance.',
          'duration_seconds': len(audio)/16000, 'decode_seconds': time.perf_counter()-started,
          'reference': benchmark.REFERENCES[0], 'transcript': text, 'previews': previews,
          'wer': benchmark.word_error_rate(benchmark.REFERENCES[0], text),
          'worker_stopped': not transcriber._worker.is_alive()}
result['passed'] = result['wer'] <= .15 and result['worker_stopped']
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
