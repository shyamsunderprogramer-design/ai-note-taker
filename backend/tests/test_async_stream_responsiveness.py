import asyncio
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.async_stream import iterate_sync


@pytest.mark.asyncio
async def test_waiting_provider_does_not_freeze_other_requests():
    release = threading.Event()
    closed = threading.Event()
    def provider():
        try:
            release.wait(1)
            yield 'first'
            yield 'second'
        finally:
            closed.set()
    stream = iterate_sync(provider())
    first = asyncio.create_task(anext(stream))
    await asyncio.sleep(.02)
    assert not first.done()
    release.set()
    assert await first == 'first'
    assert await anext(stream) == 'second'
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert closed.is_set()


@pytest.mark.asyncio
async def test_cancellation_closes_provider_after_pending_read():
    release = threading.Event()
    started = threading.Event()
    closed = threading.Event()
    def provider():
        try:
            started.set()
            release.wait(1)
            yield 'unused'
        finally:
            closed.set()
    stream = iterate_sync(provider())
    task = asyncio.create_task(anext(stream))
    await asyncio.to_thread(started.wait, 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    assert await asyncio.to_thread(closed.wait, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize('asynchronous', [False, True])
async def test_route_accepts_both_provider_protocols_after_app_import(monkeypatch, asynchronous):
    import ai_router
    from modules.platform import cloud_providers
    original = cloud_providers.ask_gpt_stream
    import core.main
    assert cloud_providers.ask_gpt_stream is original
    assert not hasattr(original, '_async_patched')
    expected = ['event: content\ndata: {"content":"answer"}\n\n', 'event: done\ndata: {}\n\n']
    def sync_provider(*args, **kwargs):
        yield from expected
    async def async_provider(*args, **kwargs):
        for item in expected:
            yield item
    monkeypatch.setattr(ai_router, 'ask_ollama_stream', async_provider if asynchronous else sync_provider)
    actual = [event async for event in ai_router.route_ai_stream('Question', provider='qa:local')]
    assert actual == expected
