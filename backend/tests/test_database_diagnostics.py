import asyncio
import ssl
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import database
from routes import _main_unique, deps


@pytest.fixture
def diagnostic_client(monkeypatch):
    import sqlalchemy.ext.asyncio

    async def lookup(token):
        if token in {"admin", "member"}:
            return SimpleNamespace(id="synthetic-user", is_admin=token == "admin")
        return None

    monkeypatch.setattr(deps, "get_current_user", lookup)
    monkeypatch.setattr(database, "HAS_SQLALCHEMY", True)
    monkeypatch.setattr(database, "DATABASE_URL",
        "postgresql+asyncpg://diag-user:sqlite-private-secret@db.example.invalid/app"
        "?sslmode=disable&prepared_statement_cache_size=9&password=query-secret")
    monkeypatch.setattr(database, "DEFAULT_SQLITE_URL", "sqlite+aiosqlite:////private-owner/app.db")
    monkeypatch.delenv("DATABASE_SSL_CA_FILE", raising=False)
    connection = MagicMock()
    connection.execute = AsyncMock(return_value=MagicMock(scalar=lambda: "synthetic-version"))
    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    engine.dispose = AsyncMock()
    factory = MagicMock(return_value=engine)
    monkeypatch.setattr(sqlalchemy.ext.asyncio, "create_async_engine", factory)
    app = FastAPI()
    app.include_router(_main_unique.router)
    with TestClient(app) as client:
        yield client, factory, engine, connection


@pytest.mark.parametrize("path", ["/health/config", "/health/db-debug"])
@pytest.mark.parametrize("token,status", [(None, 401), ("invalid", 401), ("member", 403)])
def test_diagnostics_require_admin_before_connecting(diagnostic_client, path, token, status):
    client, factory, _, _ = diagnostic_client
    response = client.get(path, headers={"Authorization": f"Bearer {token}"} if token else {})
    assert response.status_code == status
    factory.assert_not_called()


@pytest.mark.parametrize("path", ["/health/config", "/health/db-debug"])
def test_admin_diagnostics_never_return_connection_secrets(diagnostic_client, path):
    client, factory, engine, _ = diagnostic_client
    response = client.get(path, headers={"Authorization": "Bearer admin"})
    assert response.status_code == 200
    for private in ("diag-user", "sqlite-private-secret", "query-secret", "db.example.invalid", "private-owner"):
        assert private not in response.text
    if path.endswith("db-debug"):
        url = factory.call_args.args[0]
        assert "sslmode" not in url
        assert "prepared_statement_cache_size=9" in url
        context = factory.call_args.kwargs["connect_args"]["ssl"]
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        engine.dispose.assert_awaited_once()
    else:
        assert response.json()["database_type"] == "postgresql"
        factory.assert_not_called()


@pytest.mark.parametrize("phase", ["connect", "query"])
def test_failed_probe_disposes_engine_and_redacts_errors(diagnostic_client, phase, caplog):
    client, _, engine, connection = diagnostic_client
    operation = engine.begin.return_value.__aenter__ if phase == "connect" else connection.execute
    operation.side_effect = RuntimeError("synthetic-private-connection-secret")
    response = client.get("/health/db-debug", headers={"Authorization": "Bearer admin"})
    assert response.status_code == 503
    assert response.json()["status"] == "failed"
    assert "synthetic-private-connection-secret" not in response.text + caplog.text
    engine.dispose.assert_awaited_once()


def test_invalid_ca_prevents_diagnostic_connection(diagnostic_client, monkeypatch, tmp_path):
    client, factory, _, _ = diagnostic_client
    monkeypatch.setenv("DATABASE_SSL_CA_FILE", str(tmp_path / "missing-ca.pem"))
    response = client.get("/health/db-debug", headers={"Authorization": "Bearer admin"})
    assert response.status_code == 503
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_cancelled_probe_disposes_engine(diagnostic_client):
    _, _, engine, connection = diagnostic_client
    connection.execute.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await _main_unique.db_debug(SimpleNamespace(is_admin=True))
    engine.dispose.assert_awaited_once()
