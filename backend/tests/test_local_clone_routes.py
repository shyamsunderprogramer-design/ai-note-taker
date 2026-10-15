import io
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1] / 'modules/voice'))
import voice_clone_agent
from routes import voice


@pytest.fixture
def client(tmp_path, monkeypatch):
    manager = voice_clone_agent.VoiceCloneManager(str(tmp_path))
    monkeypatch.setattr(voice_clone_agent, 'voice_manager', manager)
    monkeypatch.setattr(voice, 'voice_manager', manager)
    monkeypatch.setattr(voice, 'VOICE_CLONE_AVAILABLE', True)
    app = FastAPI()
    app.include_router(voice.router)
    app.dependency_overrides[voice.require_authentication] = lambda: object()
    with TestClient(app) as http:
        yield http, manager


def reference():
    buffer = io.BytesIO()
    sf.write(buffer, np.sin(np.arange(24000 * 4) * .05) * .1, 24000, format='WAV')
    return buffer.getvalue()


def test_recording_and_transcript_survive_reload(client):
    http, manager = client
    response = http.post('/voice-clone/create', data={
        'name': 'My voice', 'engine': 'qwen_local', 'ref_text': 'These are my reference words.',
    }, files={'audio_files': ('sample.wav', reference(), 'audio/wav')})
    assert response.status_code == 200
    model_id = response.json()['model_id']
    reloaded = voice_clone_agent.VoiceCloneManager(manager.storage_dir).models[model_id]
    assert reloaded.source == 'qwen_local'
    assert reloaded.reference_text == 'These are my reference words.'
    assert Path(reloaded.reference_audio).is_file()


def test_missing_transcript_rejected_without_creating_stock_voice(client):
    http, manager = client
    response = http.post('/voice-clone/create', data={'name': 'My voice'},
                         files={'audio_files': ('sample.wav', reference(), 'audio/wav')})
    assert response.status_code == 422
    assert manager.models == {}


def test_generated_wav_served_from_manager_storage(client):
    http, manager = client
    audio_dir = Path(manager.storage_dir) / 'audio'
    audio_dir.mkdir()
    (audio_dir / 'test.wav').write_bytes(reference())
    response = http.get('/voice-clone/audio/test.wav')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/wav'
    assert response.content.startswith(b'RIFF')
