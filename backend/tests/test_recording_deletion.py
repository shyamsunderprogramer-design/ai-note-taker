from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from modules.video import recording_manager as recordings
from routes import video


@pytest.fixture
def saved_recording(tmp_path, monkeypatch):
    monkeypatch.setattr(recordings, 'RECORDINGS_DIR', str(tmp_path))
    manager = recordings.RecordingManager()
    session = manager.start('alice', title='Synthetic deletion check')
    media = Path(recordings._media_path(session.id))
    media.write_bytes(b'synthetic media')
    return manager, session, media


@pytest.mark.parametrize('failed_file', ['media', 'metadata'])
def test_failed_deletion_remains_retryable(saved_recording, monkeypatch, failed_file, caplog):
    manager, session, media = saved_recording
    metadata = Path(recordings._session_path(session.id))
    failing_path = media if failed_file == 'media' else metadata
    remove = recordings.os.remove
    def fail(path):
        if Path(path) == failing_path:
            raise PermissionError('private filesystem details')
        remove(path)
    with monkeypatch.context() as patch:
        patch.setattr(recordings.os, 'remove', fail)
        assert manager.delete(session.id) is False
    assert manager.get(session.id) is session
    assert metadata.exists()
    assert 'private filesystem details' not in caplog.text
    assert manager.delete(session.id) is True
    assert manager.get(session.id) is None
    assert not media.exists() and not metadata.exists()


def test_missing_metadata_does_not_prevent_media_removal(saved_recording):
    manager, session, media = saved_recording
    Path(recordings._session_path(session.id)).unlink()
    assert manager.delete(session.id) is True
    assert not media.exists()


def test_deletion_failure_is_not_reported_as_success(saved_recording, monkeypatch):
    manager, session, _ = saved_recording
    monkeypatch.setattr(recordings, 'get_manager', lambda: manager)
    monkeypatch.setattr(manager, 'delete', lambda _: False)
    app = FastAPI()
    app.include_router(video.router)
    app.dependency_overrides[video.require_authentication] = lambda: SimpleNamespace(id='alice')
    with TestClient(app) as client:
        result = client.delete('/recordings/' + session.id)
    assert result.status_code == 500
    assert result.json().get('status') != 'deleted'
    assert manager.get(session.id) is session
