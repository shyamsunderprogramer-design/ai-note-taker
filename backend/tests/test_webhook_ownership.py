from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from routes import webhooks


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(webhooks, '_webhook_subscriptions', {})
    app = FastAPI()
    app.include_router(webhooks.router)
    return app


@pytest.mark.parametrize('method,path', [
    ('post', '/webhooks/subscribe?url=https://example.invalid/hook'),
    ('get', '/webhooks'),
    ('delete', '/webhooks/unknown'),
    ('post', '/webhooks/test'),
])
def test_webhook_operations_require_authentication(app, method, path):
    with TestClient(app) as client:
        assert getattr(client, method)(path).status_code == 401


def test_webhooks_are_isolated_by_owner(app):
    owner = SimpleNamespace(id='alice')
    app.dependency_overrides[webhooks.require_authentication] = lambda: owner
    with TestClient(app) as client:
        created = client.post('/webhooks/subscribe', params={'url': 'https://example.invalid/alice'})
        assert created.status_code == 200
        webhook_id = created.json()['id']
        assert len(client.get('/webhooks').json()['webhooks']) == 1
        owner.id = 'bob'
        assert client.get('/webhooks').json()['webhooks'] == []
        assert client.post('/webhooks/test').json()['webhooks_notified'] == 0
        assert client.delete('/webhooks/' + webhook_id).status_code == 404
        assert webhook_id in webhooks._webhook_subscriptions
        owner.id = 'alice'
        assert client.delete('/webhooks/' + webhook_id).status_code == 200
        assert client.get('/webhooks').json()['webhooks'] == []


def test_signing_secret_uses_body_and_is_not_returned_by_listing(app):
    app.dependency_overrides[webhooks.require_authentication] = lambda: SimpleNamespace(id='alice')
    with TestClient(app) as client:
        rejected = client.post('/webhooks/subscribe', params={
            'url': 'https://example.invalid/hook', 'secret': 'synthetic-query-secret',
        })
        assert rejected.status_code == 422
        assert webhooks._webhook_subscriptions == {}
        created = client.post('/webhooks/subscribe', params={'url': 'https://example.invalid/hook'},
                              json={'secret': 'synthetic-body-secret'})
        assert created.status_code == 200
        assert created.json()['secret'] == 'synthetic-body-secret'
        assert len(created.json()['id']) == 36
        listed = client.get('/webhooks').json()['webhooks']
        assert len(listed) == 1
        assert 'secret' not in listed[0]
        preview = client.post('/webhooks/test').json()
        assert preview['status'] == 'preview'
        assert preview['matching_webhooks'] == 1
        assert preview['webhooks_notified'] == 0
