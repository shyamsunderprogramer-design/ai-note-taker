"""Check storage selection in fresh processes so import caches cannot mask leaks."""
import os
from pathlib import Path
import subprocess
import sys


def test_explicit_sqlite_and_auxiliary_storage_stay_isolated(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    env = dict(os.environ, ANT_DATA_DIR=str(tmp_path / 'data'),
               DATABASE_URL=f'sqlite+aiosqlite:///{tmp_path / "chosen.db"}',
               FORCE_SQLITE='true', TESTING='true',
               PYTHONPATH=os.pathsep.join([str(backend), str(backend / 'core')]))
    code = '''
import os
from pathlib import Path
from core import database
from security.encryption import EncryptionManager
from modules.platform.unified_database import UnifiedDatabase
assert database.DATABASE_URL == os.environ['DATABASE_URL']
root = Path(os.environ['ANT_DATA_DIR'])
assert database._DATA_DIR == root
assert Path(EncryptionManager().key_file).is_relative_to(root)
assert Path(UnifiedDatabase().db_path).is_relative_to(root)
'''
    result = subprocess.run([sys.executable, '-c', code], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_recordings_initialize_outside_backend_and_reload(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    launch = tmp_path / 'launch'
    launch.mkdir()
    env = dict(os.environ, ANT_DATA_DIR=str(tmp_path / 'data'),
               PYTHONPATH=str(backend))
    code = """
import os
from pathlib import Path
from modules.video.recording_manager import RecordingManager, RECORDINGS_DIR
root = Path(os.environ['ANT_DATA_DIR'])
assert Path(RECORDINGS_DIR).is_absolute()
assert Path(RECORDINGS_DIR) == root / 'recordings'
first = RecordingManager()
session = first.start('qa-user', title='Synthetic metadata check')
second = RecordingManager()
assert second._sessions[session.id].title == 'Synthetic metadata check'
assert not Path('data').exists(), 'launch directory must not determine storage'
"""
    result = subprocess.run([sys.executable, '-c', code], env=env, cwd=launch,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_test_mode_never_loads_dotenv(monkeypatch):
    import importlib
    import dotenv
    def forbidden(*args, **kwargs):
        raise AssertionError('test configuration must not read developer .env')
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)
    import core.config
    importlib.reload(core.config)


def test_isolated_mode_never_queries_desktop_key_server(monkeypatch):
    import ai_router
    from modules.platform import cloud_providers
    from routes import ollama
    monkeypatch.setenv('ANT_DISABLE_KEY_SERVER', '1')
    monkeypatch.delenv('QA_PROVIDER_KEY', raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('isolated run must not request personal credentials')
    monkeypatch.setattr(cloud_providers.sync_client, 'post', forbidden)
    assert cloud_providers.fetch_key_from_secure_server('qa') is None
    assert ollama._has_provider_key('qa', 'QA_PROVIDER_KEY') is False
    ai_router._warm_provider_keys()
