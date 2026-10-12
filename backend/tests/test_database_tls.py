import ssl
from unittest.mock import AsyncMock, MagicMock

import pytest

from core import database


@pytest.fixture
def engine_factory(monkeypatch):
    connection = MagicMock()
    connection.run_sync = AsyncMock()
    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=engine)
    monkeypatch.setattr(database, 'create_async_engine', factory)
    monkeypatch.setattr(database, 'async_sessionmaker', MagicMock())
    monkeypatch.setattr(database.DatabaseManager, '_run_alembic_migrations', AsyncMock())
    monkeypatch.delenv('DATABASE_SSL_CA_FILE', raising=False)
    return factory


@pytest.mark.asyncio
@pytest.mark.parametrize('query', [
    'sslmode=require&prepared_statement_cache_size=10',
    'prepared_statement_cache_size=10&sslmode=disable',
])
async def test_postgres_verifies_server_and_preserves_other_options(monkeypatch, engine_factory, query):
    monkeypatch.setattr(database, 'DATABASE_URL', 'postgresql+asyncpg://example.invalid/app?' + query)
    manager = database.DatabaseManager()
    await manager.initialize()
    assert manager._initialized
    url = engine_factory.call_args.args[0]
    assert url == 'postgresql+asyncpg://example.invalid/app?prepared_statement_cache_size=10'
    context = engine_factory.call_args.kwargs['connect_args']['ssl']
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_invalid_ca_never_opens_database_connection(monkeypatch, engine_factory, tmp_path):
    monkeypatch.setattr(database, 'DATABASE_URL', 'postgresql+asyncpg://example.invalid/app')
    monkeypatch.setenv('DATABASE_SSL_CA_FILE', str(tmp_path / 'missing-ca.pem'))
    manager = database.DatabaseManager()
    with pytest.raises(FileNotFoundError):
        await manager.initialize()
    engine_factory.assert_not_called()
    assert manager._initialized is False


def test_integration_secret_decode_failure_is_redacted(caplog):
    config = database.IntegrationConfig()
    config.secrets_encrypted = 'plain:invalid private-token-secret'
    assert config._decrypt_secrets() == {}
    assert 'could not be decoded' in caplog.text
    assert 'private-token-secret' not in caplog.text


@pytest.mark.asyncio
async def test_database_initialization_errors_do_not_log_connection_secrets(monkeypatch, engine_factory, caplog):
    engine_factory.side_effect = RuntimeError('postgresql://private:secret@example.invalid/app')
    monkeypatch.setattr(database, 'DATABASE_URL', 'postgresql+asyncpg://example.invalid/app')
    with pytest.raises(RuntimeError):
        await database.DatabaseManager().initialize()
    assert 'Initialization failed' in caplog.text
    assert 'private:secret' not in caplog.text
