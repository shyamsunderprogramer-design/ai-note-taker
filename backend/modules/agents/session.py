"""
Agent Session Manager — Manages agent sessions with DB persistence and in-memory cache.

Replaces the in-memory singletons in shadow_agent.py and realtime_suggestions.py
with a unified session model that persists to the database.
"""

import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from agents.base import TranscriptSegment, is_question

logger = logging.getLogger("agents.session")

MAX_TRANSCRIPT_BUFFER = 20  # Keep last N segments


class AgentSessionManager:
    """Manages agent sessions with DB persistence and in-memory cache."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 minutes

        # Fallback in-memory sessions when DB is unavailable
        self._memory_sessions: Dict[str, Dict] = {}
        self._has_db = None  # Lazy-check on first use

    def _check_db(self) -> bool:
        """Lazy-check if database is available."""
        if self._has_db is None:
            try:
                from database import HAS_SQLALCHEMY
                self._has_db = HAS_SQLALCHEMY
            except (ImportError, Exception):
                self._has_db = False
                logger.debug("[AgentSessionManager] Database not available, using in-memory sessions")
        return self._has_db

    def _is_cache_valid(self, session_id: str) -> bool:
        """Check if cached session is still within TTL."""
        if session_id not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[session_id]) < self._cache_ttl

    def _invalidate_cache(self, session_id: str):
        """Remove a session from the in-memory cache."""
        self._cache.pop(session_id, None)
        self._cache_timestamps.pop(session_id, None)

    async def create_session(
        self,
        user_id: str,
        session_type: str,
        active_agents: List[str],
        config: Dict = None,
        company: str = None,
        role: str = None,
        stage: str = None,
    ) -> Dict:
        """Create a new agent session. Returns session dict."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session_data = {
            "id": session_id,
            "user_id": user_id,
            "session_type": session_type,
            "state": "listening",
            "company": company or "",
            "role": role or "",
            "stage": stage or "",
            "active_agents": active_agents,
            "config": config or {},
            "transcript_buffer": [],
            "agent_states": {},
            "suggestions": [],
            "entities": {},
            "started_at": now.isoformat(),
            "ended_at": None,
            "duration_seconds": None,
        }

        # Initialize per-agent state
        for agent_type in active_agents:
            session_data["agent_states"][agent_type] = {
                "last_suggestion_time": 0,
                "suggestions_made": 0,
                "suggestions_accepted": 0,
            }
        # Meeting agent gets accumulated_notes
        if "meeting" in active_agents:
            session_data["agent_states"]["meeting"]["accumulated_notes"] = ""
        # Sales coach gets BANT/MEDDIC tracking
        if "sales_coach" in active_agents:
            session_data["agent_states"]["sales_coach"]["bant"] = {
                "budget": "unknown",
                "authority": "unknown",
                "need": "unknown",
                "timeline": "unknown",
            }
            session_data["agent_states"]["sales_coach"]["objections_detected"] = 0

        # Persist to DB
        if self._check_db():
            try:
                await self._db_create(session_data)
            except Exception as e:
                logger.warning("[AgentSessionManager] DB create failed, using memory: %s", str(e))
                self._memory_sessions[session_id] = session_data
        else:
            self._memory_sessions[session_id] = session_data

        # Cache it
        self._cache[session_id] = session_data
        self._cache_timestamps[session_id] = time.time()

        logger.info(f"[AgentSessionManager] Created session {session_id[:8]} type={session_type} agents={active_agents}")
        return session_data

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID. Uses cache first, then DB, then memory fallback."""
        # Check cache
        if session_id in self._cache and self._is_cache_valid(session_id):
            return self._cache[session_id]

        # Try DB
        if self._check_db():
            try:
                session_data = await self._db_get(session_id)
                if session_data:
                    self._cache[session_id] = session_data
                    self._cache_timestamps[session_id] = time.time()
                    return session_data
            except Exception as e:
                logger.warning("[AgentSessionManager] DB get failed: %s", str(e))

        # Memory fallback
        if session_id in self._memory_sessions:
            self._cache[session_id] = self._memory_sessions[session_id]
            self._cache_timestamps[session_id] = time.time()
            return self._memory_sessions[session_id]

        return None

    async def save_session(self, session: Dict) -> None:
        """Save session back to storage."""
        session_id = session.get("id", "")

        # Update cache
        self._cache[session_id] = session
        self._cache_timestamps[session_id] = time.time()

        # Persist to DB
        if self._check_db():
            try:
                await self._db_update(session)
                # Also update memory fallback
                self._memory_sessions[session_id] = session
                return
            except Exception as e:
                logger.warning("[AgentSessionManager] DB save failed: %s", str(e))

        # Memory fallback
        self._memory_sessions[session_id] = session

    async def end_session(self, session_id: str) -> Optional[Dict]:
        """End a session and compute final stats."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session["state"] = "ended"
        session["ended_at"] = datetime.utcnow().isoformat()

        # Calculate duration
        started = session.get("started_at", "")
        if started:
            try:
                started_dt = datetime.fromisoformat(started)
                session["duration_seconds"] = int((datetime.utcnow() - started_dt).total_seconds())
            except (ValueError, TypeError):
                pass

        await self.save_session(session)
        self._invalidate_cache(session_id)

        logger.info(f"[AgentSessionManager] Ended session {session_id[:8]} duration={session.get('duration_seconds', 0)}s")
        return session

    def add_segment(self, session: Dict, text: str, speaker: str) -> TranscriptSegment:
        """Add a transcript segment to the session buffer."""
        segment = TranscriptSegment(
            text=text,
            speaker=speaker,
            timestamp=time.time(),
            is_question=is_question(text),
        )

        buffer = session.get("transcript_buffer", [])
        buffer.append({
            "text": segment.text,
            "speaker": segment.speaker,
            "timestamp": segment.timestamp,
            "is_question": segment.is_question,
        })

        # Trim to max buffer size
        if len(buffer) > MAX_TRANSCRIPT_BUFFER:
            buffer = buffer[-MAX_TRANSCRIPT_BUFFER:]

        session["transcript_buffer"] = buffer
        return segment

    def get_transcript_window(self, session: Dict, last_n: int = 10) -> List[TranscriptSegment]:
        """Get the last N transcript segments as TranscriptSegment objects."""
        buffer = session.get("transcript_buffer", [])
        recent = buffer[-last_n:] if last_n > 0 else buffer
        return [
            TranscriptSegment(
                text=s.get("text", ""),
                speaker=s.get("speaker", "unknown"),
                timestamp=s.get("timestamp", 0),
                is_question=s.get("is_question", False),
            )
            for s in recent
        ]

    def format_transcript_window(self, session: Dict, last_n: int = 10) -> str:
        """Format transcript buffer as readable conversation text."""
        segments = self.get_transcript_window(session, last_n)
        if not segments:
            return ""

        lines = []
        for seg in segments:
            speaker_label = {
                "user": "You",
                "interviewer": "Interviewer",
                "other": "Other",
            }.get(seg.speaker, seg.speaker.capitalize())
            lines.append(f"{speaker_label}: {seg.text}")

        return "\n".join(lines)

    def update_agent_state(self, session: Dict, agent_type: str, state_update: Dict) -> None:
        """Update a specific agent's state within the session."""
        agent_states = session.get("agent_states", {})
        if agent_type not in agent_states:
            agent_states[agent_type] = {}
        agent_states[agent_type].update(state_update)
        session["agent_states"] = agent_states

    def get_agent_state(self, session: Dict, agent_type: str) -> Dict:
        """Get a specific agent's state from the session."""
        return session.get("agent_states", {}).get(agent_type, {})

    def add_suggestion(self, session: Dict, suggestion: Dict) -> None:
        """Add a suggestion to the session's suggestion list."""
        suggestions = session.get("suggestions", [])
        suggestions.append(suggestion)
        session["suggestions"] = suggestions

    def accept_suggestion(self, session: Dict, suggestion_id: str) -> Optional[Dict]:
        """Mark a suggestion as accepted."""
        suggestions = session.get("suggestions", [])
        for s in suggestions:
            if s.get("id") == suggestion_id:
                s["accepted"] = True
                s["accepted_at"] = time.time()
                # Update agent state counter
                agent_type = s.get("agent_type", "")
                agent_state = self.get_agent_state(session, agent_type)
                agent_state["suggestions_accepted"] = agent_state.get("suggestions_accepted", 0) + 1
                self.update_agent_state(session, agent_type, agent_state)
                return s
        return None

    def dismiss_suggestion(self, session: Dict, suggestion_id: str) -> Optional[Dict]:
        """Mark a suggestion as dismissed."""
        suggestions = session.get("suggestions", [])
        for s in suggestions:
            if s.get("id") == suggestion_id:
                s["dismissed"] = True
                s["dismissed_at"] = time.time()
                return s
        return None

    def get_stats(self, session: Dict) -> Dict:
        """Get session statistics."""
        suggestions = session.get("suggestions", [])
        agent_states = session.get("agent_states", {})

        return {
            "session_id": session.get("id"),
            "session_type": session.get("session_type"),
            "state": session.get("state"),
            "duration_seconds": session.get("duration_seconds"),
            "total_segments": len(session.get("transcript_buffer", [])),
            "total_suggestions": len(suggestions),
            "suggestions_accepted": len([s for s in suggestions if s.get("accepted")]),
            "suggestions_dismissed": len([s for s in suggestions if s.get("dismissed")]),
            "per_agent_stats": {
                agent_type: {
                    "suggestions_made": state.get("suggestions_made", 0),
                    "suggestions_accepted": state.get("suggestions_accepted", 0),
                    "last_active": state.get("last_suggestion_time", 0),
                }
                for agent_type, state in agent_states.items()
            },
        }

    # --- Database operations ---

    async def _db_create(self, session_data: Dict):
        """Create session row in database."""
        try:
            from database import get_async_session, AgentSession as AgentSessionModel
            async with get_async_session() as db:
                db_session = AgentSessionModel(
                    id=session_data["id"],
                    user_id=session_data["user_id"],
                    session_type=session_data["session_type"],
                    state=session_data["state"],
                    company=session_data.get("company"),
                    role=session_data.get("role"),
                    stage=session_data.get("stage"),
                    active_agents=session_data.get("active_agents", []),
                    config=session_data.get("config", {}),
                    transcript_buffer=session_data.get("transcript_buffer", []),
                    agent_states=session_data.get("agent_states", {}),
                    suggestions=session_data.get("suggestions", []),
                    entities=session_data.get("entities", {}),
                    started_at=datetime.utcnow(),
                )
                db.add(db_session)
                await db.commit()
        except Exception as e:
            logger.error("[AgentSessionManager] DB create error: %s", str(e))
            raise

    async def _db_get(self, session_id: str) -> Optional[Dict]:
        """Get session from database by ID."""
        try:
            from database import get_async_session, AgentSession as AgentSessionModel
            from sqlalchemy import select
            async with get_async_session() as db:
                result = await db.execute(
                    select(AgentSessionModel).where(AgentSessionModel.id == session_id)
                )
                row = result.scalar_one_or_none()
                if row:
                    return row.to_dict()
            return None
        except Exception as e:
            logger.error("[AgentSessionManager] DB get error: %s", str(e))
            raise

    async def _db_update(self, session: Dict):
        """Update session row in database."""
        try:
            from database import get_async_session, AgentSession as AgentSessionModel
            from sqlalchemy import select
            async with get_async_session() as db:
                result = await db.execute(
                    select(AgentSessionModel).where(AgentSessionModel.id == session["id"])
                )
                row = result.scalar_one_or_none()
                if row:
                    row.state = session.get("state", row.state)
                    row.active_agents = session.get("active_agents", row.active_agents)
                    row.config = session.get("config", row.config)
                    row.transcript_buffer = session.get("transcript_buffer", row.transcript_buffer)
                    row.agent_states = session.get("agent_states", row.agent_states)
                    row.suggestions = session.get("suggestions", row.suggestions)
                    row.entities = session.get("entities", row.entities)
                    row.ended_at = session.get("ended_at")
                    row.duration_seconds = session.get("duration_seconds")
                    await db.commit()
        except Exception as e:
            logger.error("[AgentSessionManager] DB update error: %s", str(e))
            raise


# Global singleton
session_manager = AgentSessionManager()