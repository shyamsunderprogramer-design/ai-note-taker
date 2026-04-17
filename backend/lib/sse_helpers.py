"""
Shared SSE (Server-Sent Events) helper functions.
Used by both ai_router.py and cloud_providers.py to avoid duplication.
"""

import json


def make_meta(model, provider):
    """Build SSE meta event with model and provider info."""
    data = json.dumps({"type": "meta", "model": model, "provider": provider})
    return f"event: meta\ndata: {data}\n\n"


def make_content(chunk):
    """Build SSE content event with a text chunk."""
    data = json.dumps({"type": "chunk", "content": chunk})
    return f"event: chunk\ndata: {data}\n\n"


def make_done(ms):
    """Build SSE done event with elapsed time in ms."""
    data = json.dumps({"type": "done", "ms": ms})
    return f"event: done\ndata: {data}\n\n"


def make_error(msg):
    """Build SSE error event with error message."""
    data = json.dumps({"type": "error", "message": msg})
    return f"event: error\ndata: {data}\n\n"


def make_vision(chunk, provider=""):
    """Build SSE vision event — streams image description in real-time."""
    data = json.dumps({"type": "vision", "content": chunk, "provider": provider})
    return f"event: vision\ndata: {data}\n\n"


def make_vision_done(ms, provider):
    """Build SSE vision_done event — signals Step 1 (vision description) is complete."""
    data = json.dumps({"type": "vision_done", "ms": ms, "provider": provider})
    return f"event: vision_done\ndata: {data}\n\n"