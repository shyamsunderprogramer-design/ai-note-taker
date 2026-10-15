import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core import database


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome', ['success', 'failure', 'cancel'])
async def test_api_key_loading_preserves_cancellation_and_redacts_errors(monkeypatch, caplog, outcome):
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(openai_key_encrypted='legacy-key')
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(database.db_manager, 'session_maker', factory)
    decrypt = MagicMock(return_value='decoded-key')
    if outcome == 'failure':
        decrypt.side_effect = ValueError('SHOULD_NOT_BE_LOGGED')
    elif outcome == 'cancel':
        decrypt.side_effect = asyncio.CancelledError()
    monkeypatch.setattr(database.UserAPIKeyRepository, '_get_encryption', lambda: (None, decrypt))

    if outcome == 'cancel':
        with pytest.raises(asyncio.CancelledError):
            await database.UserAPIKeyRepository.get_by_user('00000000-0000-0000-0000-000000000001')
    else:
        keys = await database.UserAPIKeyRepository.get_by_user('00000000-0000-0000-0000-000000000001')
        assert keys == ({'openai': 'decoded-key'} if outcome == 'success' else None)
    assert 'SHOULD_NOT_BE_LOGGED' not in caplog.text
