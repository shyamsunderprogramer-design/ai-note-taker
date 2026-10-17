"""Exercise BYOK authentication through FastAPI's actual dependency graph."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from routes import deps, ollama


@pytest.mark.parametrize('token,valid,expected', [(None, False, 401), ('invalid', False, 401), ('valid', True, 200)])
def test_byok_authentication(monkeypatch, token, valid, expected):
    lookup = AsyncMock(return_value=SimpleNamespace(id='qa-user') if valid else None)
    monkeypatch.setattr(deps, 'get_current_user', lookup)
    monkeypatch.setattr(ollama, 'BYOK_AVAILABLE', True)
    monkeypatch.setattr(ollama, 'get_available_providers', lambda user_id: {} if user_id == 'qa-user' else pytest.fail('wrong user'))
    monkeypatch.setattr(ollama, 'has_premium_access', lambda user_id: False)
    app = FastAPI()
    app.include_router(ollama.router)
    with TestClient(app) as client:
        response = client.get('/providers/byok/status', headers={'Authorization': f'Bearer {token}'} if token else {})
    assert response.status_code == expected
    if token:
        lookup.assert_awaited_once_with(token)
    else:
        lookup.assert_not_called()
    if expected == 200:
        assert response.json()['providers'] == {}
        assert response.json()['has_premium_access'] is False


@pytest.mark.parametrize('name', ['study', 'conversations', 'compliance', 'career', 'jobs', 'interview', 'mcp', 'admin', 'analytics', 'voice', 'auto_apply'])
def test_routes_share_awaited_authentication(name):
    import importlib
    module = importlib.import_module('routes.' + name)
    assert module.require_authentication is deps.require_authentication
