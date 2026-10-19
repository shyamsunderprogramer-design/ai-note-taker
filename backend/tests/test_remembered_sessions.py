"""Regression: persistent sessions must renew only while their login is active."""
from datetime import timedelta
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_refresh_survives_access_expiry_but_not_logout(tmp_db):
    from core.main import app
    from security.auth import user_manager, create_access_token
    user = await user_manager.create_user('remember_expiry', 'remember@example.com', 'TestPass123!')
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        login = await client.post('/auth/login', data={'username': user.username, 'password': 'TestPass123!'})
        assert login.status_code == 200
        pair = login.json()
        current = await user_manager.get_user(user.username)
        expired = create_access_token({'sub': str(user.id), 'username': user.username},
                                      expires_delta=timedelta(seconds=-10), jti=current.active_session_id)
        assert (await client.get('/auth/me', headers={'Authorization': f'Bearer {expired}'})).status_code == 401
        renewed = await client.post('/auth/refresh', data={'refresh_token': pair['refresh_token']})
        assert renewed.status_code == 200
        token = renewed.json()['access_token']
        assert (await client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})).status_code == 200
        assert (await client.post('/auth/logout', headers={'Authorization': f'Bearer {token}'})).status_code == 200
        rejected = await client.post('/auth/refresh', data={'refresh_token': pair['refresh_token']})
        assert rejected.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access_token(tmp_db):
    from core.main import app
    from security.auth import user_manager
    user = await user_manager.create_user('remember_type', 'type@example.com', 'TestPass123!')
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        login = await client.post('/auth/login', data={'username': user.username, 'password': 'TestPass123!'})
        assert login.status_code == 200
        refresh = login.json()['refresh_token']
        assert (await client.get('/auth/me', headers={'Authorization': f'Bearer {refresh}'})).status_code == 401


@pytest.mark.asyncio
async def test_login_validation_allows_cors_preflight_without_bypassing_auth(monkeypatch):
    """A browser must be able to preflight /auth/me before sending its token."""
    from core import main
    monkeypatch.setattr(main, 'AUTH_REQUIRED', True)
    origin = main.ALLOWED_ORIGINS[0]
    headers = {'Origin': origin, 'Access-Control-Request-Method': 'GET',
               'Access-Control-Request-Headers': 'authorization'}
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url='http://test') as client:
        allowed = await client.options('/auth/me', headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers['access-control-allow-origin'] == origin
        rejected = await client.options('/auth/me', headers={**headers, 'Origin': 'https://untrusted.example'})
        assert rejected.status_code == 400
        assert 'access-control-allow-origin' not in rejected.headers
        assert (await client.get('/auth/me', headers={'Origin': origin})).status_code == 401
