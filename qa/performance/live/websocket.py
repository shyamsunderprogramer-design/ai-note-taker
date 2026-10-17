"""Exercise the real live WebSocket route with paced synthetic PCM and local AI.

Uses ASGI TestClient transport, not a real meeting platform or browser.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/voice']:
    sys.path.insert(0, str(ROOT / relative))
os.environ.update(HF_HUB_OFFLINE='1', AUTH_REQUIRED='false', TESTING='true', ANT_SKIP_ALEMBIC='1')


def main(args):
    import numpy as np
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from faster_whisper.audio import decode_audio
    import whisper_handler
    whisper_handler.select_model = lambda *a, **k: 'small'
    whisper_handler.get_model(streaming=True)
    whisper_handler.model_ready.set()
    from routes import transcription
    app = FastAPI()
    app.include_router(transcription.router)
    audio = decode_audio(str(args.audio), sampling_rate=16000)
    audio = np.concatenate([audio, np.zeros(16000, dtype=np.float32)])
    rows = []
    with TestClient(app) as client:
        # Reconnect between turns to exercise session cleanup as well.
        for run in range(3):
            messages = queue.Queue()
            with client.websocket_connect('/ws/transcribe?source=system&role=software%20engineer&resume=Built%20a%20cache%20that%20reduced%20latency%20by%2020%20percent') as ws:
                assert ws.receive_json()['type'] == 'auth_ok'
                def read():
                    try:
                        while True:
                            message = ws.receive_json()
                            messages.put((time.perf_counter(), message))
                    except Exception:
                        pass
                reader = threading.Thread(target=read, daemon=True)
                reader.start()
                started = time.perf_counter()
                for offset in range(0, len(audio), 1600):
                    ws.send_bytes(audio[offset:offset+1600].astype('<f4').tobytes())
                    time.sleep(.1)
                ended = time.perf_counter()
                events = []
                deadline = ended + 30
                while time.perf_counter() < deadline:
                    try:
                        at, message = messages.get(timeout=max(.01, deadline-time.perf_counter()))
                    except queue.Empty:
                        break
                    events.append(dict(after_send_seconds=at-ended, **message))
                    if message.get('type') == 'suggestion' and not message.get('partial') and not message.get('preview') and 'measure' in message.get('question', '').lower():
                        break
                answers = [e for e in events if e.get('type') == 'suggestion' and not e.get('preview') and not e.get('partial')]
                rows.append(dict(run=run+1, audio_send_seconds=ended-started,
                                 passed=bool(answers and answers[-1].get('text') and all(word in answers[-1].get('question', '').lower() for word in ['problem', 'change', 'measure', 'result'])),
                                 events=events))
            reader.join(timeout=2)
    report = dict(passed=all(r['passed'] for r in rows), samples=rows,
                  limits='Three repeats of one synthetic interview prompt; real route, VAD, Whisper small and local live AI. In-process ASGI transport, auth disabled only in harness. No microphone, meeting platform or visible UI.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, default=Path('/tmp/ant-product-benchmark/speech-1.aiff'))
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
