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
