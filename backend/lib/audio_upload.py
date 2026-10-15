"""Run uploaded-file inference off the event loop and always remove its temp file."""
import asyncio
import os


async def transcribe_saved_upload(transcriber, path, **kwargs):
    def work():
        try:
            return transcriber(path, **kwargs)
        finally:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    return await asyncio.to_thread(work)
