"""Interview/resume routes must enforce authentication on their own."""
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import deps, interview


PROTECTED_ROUTES = [
    (method, re.sub(r"\{[^}]+\}", "synthetic", route.path))
    for route in interview.router.routes
    for method in route.methods
]


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
@pytest.mark.parametrize("token", [None, "invalid"])
def test_every_interview_route_rejects_unauthenticated_access(monkeypatch, method, path, token):
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(deps, "get_current_user", lookup)
    app = FastAPI()
    app.include_router(interview.router)
    with TestClient(app) as client:
        response = client.request(method, path, headers={"Authorization": f"Bearer {token}"} if token else {})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    if token:
        lookup.assert_awaited_once_with(token)
    else:
        lookup.assert_not_awaited()


def test_authenticated_request_reaches_interview_handler(monkeypatch):
    lookup = AsyncMock(return_value=SimpleNamespace(id="synthetic-user"))
    monkeypatch.setattr(deps, "get_current_user", lookup)
    monkeypatch.setattr(interview, "UNIFIED_LIBRARY_AVAILABLE", False)
    app = FastAPI()
    app.include_router(interview.router)
    with TestClient(app) as client:
        response = client.get("/questions/v2/categories", headers={"Authorization": "Bearer valid"})
    # The handler's documented unavailable response confirms that auth completed
    # without loading the real question database or calling any model.
    assert response.status_code == 503
    lookup.assert_awaited_once_with("valid")
