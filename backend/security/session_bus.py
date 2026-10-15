"""
Per-user async pubsub for session lifecycle events.

Used by the ``/auth/events`` SSE endpoint to push ``session_kicked``
events to a connected client when the same user's active session
changes. One ``asyncio.Queue`` per subscriber; the SSE generator
reads from the queue.

v1: in-memory only. This works fine for a single-process backend but
limits horizontal scale to one process per deployment. A future
PR can swap the in-memory dict for a Redis pub/sub channel; the
public surface (``subscribe`` / ``unsubscribe`` / ``publish``) is
deliberately backend-agnostic so the swap is local to this file.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("security.session_bus")


class SessionBus:
    """Per-user async pubsub for session lifecycle events."""

    def __init__(self):
        # user_id (str) -> set of asyncio.Queue (one per active subscriber)
        self._subs: Dict[str, set] = {}

    def subscribe(self, user_id: str) -> asyncio.Queue:
        """Register a new subscriber for the given user. Returns the
        queue the SSE generator should read from. The caller is
        responsible for calling ``unsubscribe(user_id, queue)`` when
        the SSE stream disconnects, otherwise the queue is leaked.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=32)
        self._subs.setdefault(user_id, set()).add(q)
        logger.debug("session_bus: subscribed to user_id=%s (now %d subscribers)", user_id, len(self._subs[user_id]))
        return q

    def unsubscribe(self, user_id: str, q: asyncio.Queue) -> None:
        """Remove a subscriber. Idempotent — safe to call twice for
        the same queue, or for a queue that was never registered.
        """
        subs = self._subs.get(user_id)
        if not subs:
            return
        subs.discard(q)
        if not subs:
            del self._subs[user_id]
        logger.debug("session_bus: unsubscribed from user_id=%s (remaining %d)", user_id, len(subs))

    def publish(self, user_id: str, event: Dict[str, Any]) -> None:
        """Push an event to every current subscriber of the user. The
        event dict is fanned out by reference (callers should not
        mutate it after publishing). If a subscriber's queue is full,
        the event is dropped for that subscriber and a warning is
        logged — the SSE generator can detect the gap via a periodic
        ping and reconnect.
        """
        subs = self._subs.get(user_id)
        if not subs:
            return
        for q in list(subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "session_bus: dropping event for user_id=%s (subscriber queue full)",
                    user_id,
                )

    def subscriber_count(self, user_id: Optional[str] = None) -> int:
        """Diagnostic — total active subscribers (optionally for one
        user). Used by the test suite to assert no leaks.
        """
        if user_id is None:
            return sum(len(s) for s in self._subs.values())
        return len(self._subs.get(user_id, set()))


# Singleton, mirroring the ``user_manager`` pattern in
# ``security.auth``. Imported wherever a publish or subscribe is
# needed: ``from security.session_bus import session_bus``.
session_bus = SessionBus()
