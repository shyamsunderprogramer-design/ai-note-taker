"""
Shared SSE (Server-Sent Events) helper functions.
Used by both ai_router.py and cloud_providers.py to avoid duplication.

Wire format:
    event: <type>\\ndata: <json>\\n\\n

The trailing blank line is mandatory per the SSE spec — clients split
events on it. The data payload is always a JSON object with a "type"
field that mirrors the event name.
"""

import json


def _frame(event: str, payload: dict) -> str:
    """Render one SSE event frame.

    Args:
        event: The SSE event type (e.g. "meta", "chunk", "done").
        payload: Dict to serialize as the data payload. A "type" field
            equal to ``event`` is added automatically — callers can
            omit it.

    Returns:
        String formatted as ``event: <type>\\ndata: <json>\\n\\n``.
    """
    payload = {"type": event, **payload}
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def make_meta(model: str, provider: str) -> str:
    """Stream-start frame: identifies the model + provider."""
    return _frame("meta", {"model": model, "provider": provider})


def make_content(text: str) -> str:
    """A chunk of streamed text."""
    return _frame("chunk", {"content": text})


def make_done(ms: int) -> str:
    """End-of-stream frame carrying elapsed milliseconds."""
    return _frame("done", {"ms": ms})


def make_error(message: str) -> str:
    """Error frame carrying a human-readable message."""
    return _frame("error", {"message": message})


def make_vision(content: str, provider: str = "") -> str:
    """Vision-provider description chunk (Step 1 of two-step flow)."""
    return _frame("vision", {"content": content, "provider": provider})


def make_vision_done(ms: int, provider: str) -> str:
    """Marks the end of the vision step."""
    return _frame("vision_done", {"ms": ms, "provider": provider})