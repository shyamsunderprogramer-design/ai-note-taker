import asyncio
import threading
import time

from fastapi import FastAPI
import httpx
import pytest
from modules.interview.mock_interview_library import MockInterviewLibrary
from routes import interview


def test_catalogue_is_bounded_and_stable():
    library = MockInterviewLibrary()
    first = library.get_all_questions()
    assert len(first) == 1000
    assert [q.id for q in first] == [q.id for q in library.get_all_questions()]
    assert library.get_stats()['total_questions_available'] == 1000
    with pytest.raises(ValueError):
        MockInterviewLibrary(preload_count=10000000)


@pytest.mark.asyncio
async def test_loading_does_not_block_health_and_pages_are_stable(monkeypatch):
    library = MockInterviewLibrary(preload_count=25)
    original = library._load_preload
    entered = threading.Event()
    def slow_load():
        entered.set()
        time.sleep(0.3)
        original()
    monkeypatch.setattr(library, '_load_preload', slow_load)
    monkeypatch.setattr(interview, 'mock_library', library)
    monkeypatch.setattr(interview, 'MOCK_LIBRARY_AVAILABLE', True)
    app = FastAPI()
    app.include_router(interview.router)
    @app.get('/health')
    async def health():
        return {'status': 'ok'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        pending = asyncio.create_task(client.get('/mock-interview/questions?limit=10'))
        assert await asyncio.to_thread(entered.wait, 2)
        assert (await client.get('/health')).status_code == 200
        assert not pending.done(), 'catalogue generation blocked the event loop'
        first = (await pending).json()
        second = (await client.get('/mock-interview/questions?limit=10&offset=10')).json()
        assert first['total'] == second['total'] == 25
        assert len(first['questions']) == len(second['questions']) == 10
        assert not ({q['id'] for q in first['questions']} & {q['id'] for q in second['questions']})

@pytest.mark.parametrize('count', [1, 3, 5, 7, 10])
def test_practice_set_returns_requested_count(count):
    library = MockInterviewLibrary(preload_count=10)
    questions = library.get_practice_set('Software Engineer', count)
    assert len(questions) == count
    assert len({q.id for q in questions}) == count
