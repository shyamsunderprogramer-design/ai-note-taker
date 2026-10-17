"""Route authentication must resolve the user, never accept a coroutine."""
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from routes import deps


ROUTES = ["admin", "analytics", "auto_apply", "career", "compliance",
          "conversations", "interview", "jobs", "mcp", "ollama", "study"]


@pytest.mark.parametrize("name", ROUTES)
@pytest.mark.parametrize("token,valid,expected", [
    (None, False, 401), ("invalid", False, 401), ("valid", True, 200),
])
def test_route_requires_completed_user_lookup(monkeypatch, name, token, valid, expected):
    module = importlib.import_module("routes." + name)
    user = SimpleNamespace(id="synthetic-user")
    lookup = AsyncMock(return_value=user if valid else None)
    monkeypatch.setattr(deps, "get_current_user", lookup)
    app = FastAPI()

    # Exercise each route module's dependency through FastAPI, without running
    # its business action (backup, CRM sync, model download, etc.).
    @app.get("/protected")
    def protected(authenticated=Depends(module.require_authentication)):
        return {"user_id": authenticated.id}

    with TestClient(app) as client:
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"} if token else {})
    assert response.status_code == expected
    if token:
        lookup.assert_awaited_once_with(token)
    else:
        lookup.assert_not_called()
    if expected == 200:
        assert response.json() == {"user_id": user.id}
    else:
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("is_admin,expected", [(False, 403), (True, 200)])
def test_admin_role_check_uses_authenticated_user(monkeypatch, is_admin, expected):
    from routes import admin

    lookup = AsyncMock(return_value=SimpleNamespace(id="synthetic-user", is_admin=is_admin))
    monkeypatch.setattr(deps, "get_current_user", lookup)
    app = FastAPI()

    @app.get("/admin-probe")
    def protected(user=Depends(admin.require_admin)):
        return {"user_id": user.id}

    with TestClient(app) as client:
        response = client.get("/admin-probe", headers={"Authorization": "Bearer valid"})
    assert response.status_code == expected
    lookup.assert_awaited_once_with("valid")
