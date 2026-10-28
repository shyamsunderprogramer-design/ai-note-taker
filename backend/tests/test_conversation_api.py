from types import SimpleNamespace
import uuid
from fastapi import FastAPI
import httpx
import pytest
from routes import conversations, deps
from core.database import UserRepository


@pytest.mark.asyncio
async def test_conversation_round_trip_and_user_isolation(tmp_db):
    users = [await UserRepository.create(username='qa_'+uuid.uuid4().hex[:8], email=uuid.uuid4().hex+'@example.com', hashed_password='test-only') for _ in range(2)]
    assert all(users)
    app = FastAPI()
    app.include_router(conversations.router)
    current = [users[0]]
    app.dependency_overrides[deps.require_authentication] = lambda: SimpleNamespace(id=current[0].id)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        payload = {'title':'Saved QA chat', 'messages':[{'role':'user','text':'Hello'}]}
        response = await client.post('/conversations', json=payload)
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved['messages'] == payload['messages']
        url = '/conversations/'+saved['id']
        assert (await client.get(url)).json()['title'] == payload['title']
        assert len((await client.get('/conversations')).json()) == 1
        current[0] = users[1]
        assert (await client.get('/conversations')).json() == []
        assert (await client.get(url)).status_code == 404
        assert (await client.delete(url)).status_code == 404
        current[0] = users[0]
        assert (await client.delete(url)).status_code == 200
        assert (await client.get(url)).status_code == 404
