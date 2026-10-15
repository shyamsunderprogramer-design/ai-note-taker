"""Uploaded audio must be resampled, silence-safe, and return plain text."""
import importlib.util
import sys
import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture
def handler():
    path = Path(__file__).resolve().parents[1] / 'modules/voice/whisper_handler.py'
    spec = importlib.util.spec_from_file_location('uploaded_audio_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('audio', [np.array([]), np.zeros(16000), np.array([np.nan])])
def test_empty_silent_or_invalid_audio_never_calls_model(handler, monkeypatch, audio):
    monkeypatch.setattr(handler, '_decode_audio_file', lambda path: audio)
    def unexpected(*args, **kwargs):
        pytest.fail('Silence must not reach Whisper')
    monkeypatch.setattr(handler, 'transcribe', unexpected)
    assert handler.transcribe_audio('silent.wav') == ''


def test_mobile_audio_resampled_and_text_unwrapped(handler, monkeypatch):
    calls = []
    def decode(path, sampling_rate):
        calls.append((path, sampling_rate))
        return np.array([.1, -.2], dtype=np.float32)
    monkeypatch.setitem(sys.modules, 'faster_whisper.audio', SimpleNamespace(decode_audio=decode))
    monkeypatch.setattr(handler, 'transcribe', lambda *a, **k: {'text': 'Review the budget.', 'language': 'en'})
    assert handler.transcribe_audio('recording.m4a', fast=True) == 'Review the budget.'
    assert calls == [('recording.m4a', 16000)]


@pytest.mark.asyncio
async def test_failed_transcription_removes_temporary_audio(tmp_path):
    from lib.audio_upload import transcribe_saved_upload
    path = tmp_path / 'upload.wav'
    path.write_bytes(b'audio')
    def fail(*args):
        raise ValueError('decoder failed')
    with pytest.raises(ValueError):
        await transcribe_saved_upload(fail, path)
    assert not path.exists()


@pytest.mark.asyncio
async def test_cancelled_request_still_cleans_audio_after_inference(tmp_path):
    from lib.audio_upload import transcribe_saved_upload
    path = tmp_path / 'upload.wav'
    path.write_bytes(b'audio')
    started, release = threading.Event(), threading.Event()
    def infer(*args):
        started.set()
        release.wait(1)
        return 'text'
    task = asyncio.create_task(transcribe_saved_upload(infer, path))
    assert await asyncio.to_thread(started.wait, 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    for _ in range(100):
        if not path.exists(): break
        await asyncio.sleep(.01)
    assert not path.exists()
