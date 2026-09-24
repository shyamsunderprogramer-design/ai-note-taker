"""Authentication must complete before accepting live audio or reserving a channel."""
from unittest.mock import AsyncMock
from pathlib import Path
import sys

for relative in ['core', 'modules/ai', 'modules/voice']:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / relative))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.parametrize('path,first_message', [
    ('/ws/transcribe?source=system&token=invalid', None),
    ('/ws/transcribe?source=system', {'type': 'auth', 'token': 'invalid'}),
    ('/ws?token=invalid', None),
])
def test_invalid_token_rejected_without_audio_channel_leak(monkeypatch, path, first_message):
    from routes import transcription
    monkeypatch.setattr(transcription, 'AUTH_REQUIRED', True)
    monkeypatch.setattr(transcription, 'WHISPER_AVAILABLE', True)
    validate = AsyncMock(return_value=None)
    monkeypatch.setattr(transcription, 'get_current_user', validate)
    before = transcription._DUAL_CHANNEL['system']
    app = FastAPI()
    app.include_router(transcription.router)
    with TestClient(app) as client:
        with client.websocket_connect(path) as ws:
            if first_message:
                ws.send_json(first_message)
            response = ws.receive_json()
            assert response.get('type') == 'auth_error' or response.get('error', {}).get('code') == 'INVALID_TOKEN'
            close = ws.receive()
            assert close['type'] == 'websocket.close'
            assert close['code'] == 4001
    validate.assert_awaited_once_with('invalid')
    assert transcription._DUAL_CHANNEL['system'] == before
