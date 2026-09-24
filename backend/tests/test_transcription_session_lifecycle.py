"""Exercise the real WebSocket route with deterministic speech decoding."""
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

for relative in ['core', 'modules/ai', 'modules/voice', 'modules/platform']:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / relative))


@pytest.mark.parametrize('graceful', [True, False])
def test_session_stops_worker_and_graceful_final_keeps_tail(monkeypatch, graceful):
    from routes import transcription
    import whisper_handler as speech
    workers = []
    class TrackedTranscriber(speech.BrowserTranscriber):
        def start_worker(self):
            worker = super().start_worker()
            if worker not in workers:
                workers.append(worker)
            return worker
    monkeypatch.setattr(transcription, 'AUTH_REQUIRED', False)
    monkeypatch.setattr(transcription, 'WHISPER_AVAILABLE', True)
    monkeypatch.setattr(transcription, 'BrowserTranscriber', TrackedTranscriber)
    monkeypatch.setitem(sys.modules, 'modules.voice.vibevoice_diarizer',
                        SimpleNamespace(get_streaming_diarizer=lambda: None))
    threads = []
    def decode(audio, *a, **k):
        threads.append(threading.current_thread().name)
        return {'text': 'first phrase' if len(audio) > 16000 else 'last word'}
    monkeypatch.setattr(speech, 'transcribe', decode)
    app = FastAPI()
    app.include_router(transcription.router)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/transcribe?assist=false') as ws:
            assert ws.receive_json()['type'] == 'auth_ok'
            audio = np.concatenate([np.full(48000, .02), np.zeros(3200), np.full(4800, .02)]).astype(np.float32)
            ws.send_bytes(audio.tobytes())
            if graceful:
                ws.send_json({'type': 'stop'})
                while True:
                    event = ws.receive_json()
                    if event['type'] == 'final':
                        break
                assert event['text'] == 'first phrase last word'
    for worker in workers:
        worker.join(2)
    assert workers and all(not worker.is_alive() for worker in workers)
    assert all(name.startswith('whisper') for name in threads)
