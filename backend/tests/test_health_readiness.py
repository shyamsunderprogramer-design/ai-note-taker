import pytest
from routes import health
from core import database


def test_health_uses_canonical_database_and_readiness(monkeypatch):
    assert health.db_manager is database.db_manager
    monkeypatch.setattr(health, 'DATABASE_AVAILABLE', True)
    monkeypatch.setattr(database.db_manager, '_initialized', False)
    assert health.health()['status'] == 'ok'
    assert health.readiness().status_code == 503
    monkeypatch.setattr(database.db_manager, '_initialized', True)
    assert health.readiness().status_code == 200


def test_optional_health_probe_is_off_event_loop_and_counts_local_model(monkeypatch):
    import inspect
    from routes import ollama
    assert not inspect.iscoroutinefunction(health.health_modules)
    monkeypatch.setenv('ANT_DISABLE_KEY_SERVER', '1')
    monkeypatch.setattr(ollama, '_probe_ollama', lambda: {'available':True, 'models':['qa:local']})
    response = health.health_modules()
    assert response['modules']['ai_router']['providers']['ollama'] is True
    assert response['modules']['ai_router']['status'] == 'green'
