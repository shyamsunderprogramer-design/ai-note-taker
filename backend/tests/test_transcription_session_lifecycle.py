"""Exercise the real WebSocket route with deterministic speech decoding."""
from pathlib import Path
import sys
import threading
import time
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


@pytest.mark.parametrize("manual", [True, False])
def test_questions_only_emits_question_without_backend_answer(monkeypatch, manual):
    from routes import transcription
    import whisper_handler as speech
    monkeypatch.setattr(transcription, 'AUTH_REQUIRED', False)
    monkeypatch.setattr(transcription, 'WHISPER_AVAILABLE', True)
    monkeypatch.setitem(sys.modules, 'modules.voice.vibevoice_diarizer',
                        SimpleNamespace(get_streaming_diarizer=lambda: None))
    decode = lambda *a, **k: {'text': 'Please complete this function'}
    monkeypatch.setattr(transcription, 'transcribe', decode)
    monkeypatch.setattr(speech, 'transcribe', decode)
    app = FastAPI(); app.include_router(transcription.router)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/transcribe?source=system&assist=true&questions_only=true') as ws:
            assert ws.receive_json()['type'] == 'auth_ok'
            ws.send_bytes(np.full(32000, .02, dtype=np.float32).tobytes())
            if manual:
                ws.send_json({'type':'cut'})
            else:
                ws.send_bytes(np.zeros(32000, dtype=np.float32).tobytes())
            while True:
                event = ws.receive_json()
                assert event['type'] != 'suggestion'
                if event['type'] == 'question':
                    assert event['question'] == 'Please complete this function'
                    assert event['source'] == 'system'
                    assert event['session_id'] and event['answer_id'] == 1
                    break
            ws.send_json({'type':'stop'})

@pytest.mark.parametrize('text', ['Fix this error', 'Complete this function', 'Why that approach?', 'Write this function'])
def test_short_screen_requests_are_answerable(text):
    from routes.transcription import _should_answer
    assert _should_answer(text)

@pytest.mark.parametrize('text', ['And then you use this.', 'Our hearts are full of joy.', 'We agreed to send the report by Friday.'])
def test_statements_do_not_occupy_live_answer_queue(text):
    from routes.transcription import _should_answer
    assert not _should_answer(text)

def test_live_mic_question_survives_remote_channel_ownership_without_duplicate_asr(monkeypatch):
    from routes import transcription
    import whisper_handler as speech
    monkeypatch.setattr(transcription, 'AUTH_REQUIRED', False)
    monkeypatch.setattr(transcription, 'WHISPER_AVAILABLE', True)
    monkeypatch.setitem(sys.modules, 'modules.voice.vibevoice_diarizer', SimpleNamespace(get_streaming_diarizer=lambda: None))
    monkeypatch.setitem(transcription._DUAL_CHANNEL, 'system', 1)
    monkeypatch.setitem(transcription._DUAL_CHANNEL, 'last_system_speech', time.time())
    class NoProvisionalPass(speech.BrowserTranscriber):
        def add_chunk(self, chunk):
            raise AssertionError('Live helper must not run duplicate partial ASR')
    monkeypatch.setattr(transcription, 'BrowserTranscriber', NoProvisionalPass)
    monkeypatch.setattr(transcription, 'transcribe', lambda *a, **k: {'text':'How would you design a CI/CD pipeline?'})
    app=FastAPI();app.include_router(transcription.router)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/transcribe?assist=true&questions_only=true') as ws:
            assert ws.receive_json()['type']=='auth_ok'
            ws.send_bytes(np.full(32000,.02,dtype=np.float32).tobytes())
            ws.send_bytes(np.zeros(32000,dtype=np.float32).tobytes())
            activity=False
            while True:
                event=ws.receive_json()
                activity |= event['type']=='activity'
                if event['type']=='question':
                    assert event['question']=='How would you design a CI/CD pipeline?'
                    assert activity
                    break
            ws.send_json({'type':'stop'})


def test_completed_statement_is_retained_without_triggering_an_answer(monkeypatch):
    from routes import transcription
    import whisper_handler as speech
    monkeypatch.setattr(transcription, 'AUTH_REQUIRED', False)
    monkeypatch.setattr(transcription, 'WHISPER_AVAILABLE', True)
    monkeypatch.setitem(sys.modules, 'modules.voice.vibevoice_diarizer',
                        SimpleNamespace(get_streaming_diarizer=lambda: None))
    decode = lambda *a, **k: {'text': 'We agreed to send the report on Friday.'}
    monkeypatch.setattr(transcription, 'transcribe', decode)
    monkeypatch.setattr(speech, 'transcribe', decode)
    app = FastAPI()
    app.include_router(transcription.router)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/transcribe?source=system&assist=true&questions_only=true') as ws:
            assert ws.receive_json()['type'] == 'auth_ok'
            ws.send_bytes(np.full(32000, .02, dtype=np.float32).tobytes())
            ws.send_bytes(np.zeros(32000, dtype=np.float32).tobytes())
            while True:
                event = ws.receive_json()
                assert event['type'] not in ('suggestion', 'question')
                if event['type'] == 'utterance':
                    assert event['text'] == 'We agreed to send the report on Friday.'
                    assert event['source'] == 'system'
                    assert event['session_id'] and event['utterance_id']
                    break
            ws.send_json({'type': 'stop'})
