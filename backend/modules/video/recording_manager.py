"""
recording_manager.py - Video Recording Management (T23)
Screen recording alongside audio, camera overlay, save/search/export.
"""
import os
import json
import uuid
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger("recording_manager")

RECORDINGS_DIR = os.path.join("data", "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)


@dataclass
class RecordingSession:
    id: str
    user_id: str
    title: str = "Untitled Recording"
    status: str = "idle"  # idle | recording | paused | completed | error
    source: str = "screen"  # screen | camera | both
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    file_path: Optional[str] = None
    size_bytes: int = 0
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


def _session_path(session_id: str) -> str:
    return os.path.join(RECORDINGS_DIR, f"{session_id}.json")


def _media_path(session_id: str, ext: str = "webm") -> str:
    return os.path.join(RECORDINGS_DIR, f"{session_id}.{ext}")


class RecordingManager:
    """Manages video recording sessions."""

    def __init__(self):
        self._sessions: Dict[str, RecordingSession] = {}
        self._load_existing()

    def _load_existing(self):
        """Load existing recording metadata from disk."""
        for fname in os.listdir(RECORDINGS_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(RECORDINGS_DIR, fname)) as f:
                        data = json.load(f)
                    session = RecordingSession(**data)
                    self._sessions[session.id] = session
                except Exception as e:
                    logger.error("Failed to load recording %s: %s", fname, e)

    def start(self, user_id: str, title: str = "", source: str = "screen", metadata: Dict = None) -> RecordingSession:
        """Start a new recording session."""
        session_id = str(uuid.uuid4())[:12]
        session = RecordingSession(
            id=session_id,
            user_id=user_id,
            title=title or "Untitled Recording",
            source=source,
            status="recording",
            started_at=datetime.now(),
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._save(session)
        logger.info("[Recording] Started %s for user %s", session_id, user_id)
        return session

    def stop(self, session_id: str, duration_seconds: float = 0, size_bytes: int = 0) -> Optional[RecordingSession]:
        """Stop a recording session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.status = "completed"
        session.ended_at = datetime.now()
        session.duration_seconds = duration_seconds
        session.size_bytes = size_bytes
        self._save(session)
        logger.info("[Recording] Stopped %s, duration=%.1fs", session_id, duration_seconds)
        return session

    def pause(self, session_id: str) -> Optional[RecordingSession]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.status = "paused"
        self._save(session)
        return session

    def resume(self, session_id: str) -> Optional[RecordingSession]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.status = "recording"
        self._save(session)
        return session

    def get(self, session_id: str) -> Optional[RecordingSession]:
        return self._sessions.get(session_id)

    def list_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[RecordingSession]:
        """List recordings for a user, newest first."""
        user_sessions = [s for s in self._sessions.values() if s.user_id == user_id]
        user_sessions.sort(key=lambda s: s.created_at, reverse=True)
        return user_sessions[offset:offset + limit]

    def search(self, user_id: str, query: str) -> List[RecordingSession]:
        """Search recordings by title."""
        results = []
        q = query.lower()
        for s in self._sessions.values():
            if s.user_id == user_id and q in s.title.lower():
                results.append(s)
        results.sort(key=lambda s: s.created_at, reverse=True)
        return results

    def delete(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if not session:
            return False
        try:
            os.remove(_session_path(session_id))
            media = _media_path(session_id)
            if os.path.exists(media):
                os.remove(media)
        except OSError:
            pass
        logger.info("[Recording] Deleted %s", session_id)
        return True

    def export(self, session_id: str, format: str = "json") -> Optional[Dict]:
        """Export recording metadata."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        data = asdict(session)
        if format == "markdown":
            md = f"# {session.title}\n\n"
            md += f"- **ID**: {session.id}\n"
            md += f"- **Duration**: {session.duration_seconds:.1f}s\n"
            md += f"- **Size**: {session.size_bytes} bytes\n"
            md += f"- **Source**: {session.source}\n"
            md += f"- **Started**: {session.started_at}\n"
            return {"format": "markdown", "content": md}
        return {"format": "json", "data": data}

    def _save(self, session: RecordingSession):
        try:
            data = asdict(session)
            # Convert datetime objects to ISO strings for JSON serialization
            for key in ["started_at", "ended_at", "created_at"]:
                if data.get(key) and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
            with open(_session_path(session.id), "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save recording %s: %s", session.id, e)


# Global instance
recording_manager = RecordingManager()


def get_manager() -> RecordingManager:
    return recording_manager
