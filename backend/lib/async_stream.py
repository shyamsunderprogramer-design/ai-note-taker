"""Iterate blocking provider streams without freezing the async event loop."""
import asyncio


async def iterate_sync(source):
    iterator = iter(source)
    sentinel = object()
    pending = None

    def close(completed=None):
        if completed is not None:
            # Retrieve background errors even when the caller was cancelled.
            try:
                completed.result()
            except (Exception, asyncio.CancelledError):
                pass
        closer = getattr(iterator, 'close', None)
        if closer:
            closer()

    try:
        while True:
            pending = asyncio.create_task(asyncio.to_thread(next, iterator, sentinel))
            item = await asyncio.shield(pending)
            if item is sentinel:
                break
            yield item
    finally:
        # Never close a generator while a worker is executing its next().
        if pending is not None and not pending.done():
            pending.add_done_callback(close)
        else:
            close()
