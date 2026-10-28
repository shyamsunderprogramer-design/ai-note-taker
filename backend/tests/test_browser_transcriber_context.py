from pathlib import Path
import threading

import numpy as np
import pytest


@pytest.fixture
def speech(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    for relative in ['core', 'modules/ai', 'modules/voice', 'modules/platform']:
        monkeypatch.syspath_prepend(str(root / relative))
    from modules.voice import whisper_handler
    return whisper_handler


def audio(seconds, level=.02):
    return np.full(int(seconds * 16000), level, dtype=np.float32)


def test_preview_waits_for_quiet_boundary(speech):
    transcriber = speech.BrowserTranscriber()
    transcriber.add_chunk(audio(3))
    assert transcriber._chunk_queue.empty()  # do not cut through continuous speech
    transcriber.add_chunk(audio(.3, 0))
    phrase = transcriber._chunk_queue.get_nowait()
    assert 3.1 * 16000 <= len(phrase) <= 3.3 * 16000


def test_large_packet_consumed_and_continuous_speech_bounded(speech):
    transcriber = speech.BrowserTranscriber()
    transcriber.add_chunk(audio(17))
    assert transcriber._chunk_queue.qsize() == 2
    assert len(transcriber.buffer) == 16000
    assert len(transcriber._chunk_queue.get_nowait()) == 8 * 16000


def test_final_drains_pending_phrases_before_short_tail(speech, monkeypatch):
    calls = []
    def transcribe(segment, *a, **k):
        calls.append(len(segment))
        return {'text': 'full phrase' if len(segment) > 16000 else 'last word'}
    monkeypatch.setattr(speech, 'transcribe', transcribe)
    transcriber = speech.BrowserTranscriber()
    transcriber.add_chunk(np.concatenate([audio(3), audio(.2, 0), audio(.3)]))
    try:
        assert transcriber.get_final() == 'full phrase last word'
        assert len(calls) == 2
    finally:
        transcriber.stop()
    assert not transcriber._worker.is_alive()


def test_silence_not_decoded_and_start_is_idempotent(speech, monkeypatch):
    monkeypatch.setattr(speech, 'transcribe', lambda *a, **k: pytest.fail('silence decoded'))
    transcriber = speech.BrowserTranscriber()
    worker = transcriber.start_worker()
    assert transcriber.start_worker() is worker
    transcriber.add_chunk(audio(10, 0))
    try:
        assert transcriber.get_final() == ''
    finally:
        transcriber.stop()
    assert not worker.is_alive()


def test_disconnect_suppresses_inflight_callback(speech, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def transcribe(*a, **k):
        entered.set()
        release.wait(3)
        return {'text': 'stale preview'}
    monkeypatch.setattr(speech, 'transcribe', transcribe)
    transcriber = speech.BrowserTranscriber()
    seen = []
    transcriber.add_callback(seen.append)
    worker = transcriber.start_worker()
    transcriber.add_chunk(audio(8))
    assert entered.wait(2)
    transcriber.stop()
    release.set()
    worker.join(2)
    assert not worker.is_alive()
    assert seen == []
    transcriber.add_chunk(audio(8))
    assert transcriber._chunk_queue.empty()


@pytest.mark.parametrize('heard,expected', [
    ('Explain cash invalidation.', 'Explain cache invalidation.'),
    ('The cash hit rate improved.', 'The cache hit rate improved.'),
    ('Cash miss rate increased.', 'Cache miss rate increased.'),
    ('We need cash flow for the business.', 'We need cash flow for the business.'),
    ('Our cash balance fell.', 'Our cash balance fell.'),
    ('Count cash in the register.', 'Count cash in the register.'),
    ('We tested the cash change.', 'We tested the cash change.'),
])
def test_homophones_require_computing_phrase(speech, heard, expected):
    assert speech.normalize_technical_homophones(heard) == expected
