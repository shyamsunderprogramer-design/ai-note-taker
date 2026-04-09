"""
Collaboration Mode (Duo Alternative)
Real-time collaboration feature for interview assistance
Allows trusted friend/mentor to join and help during interview
"""

import json
import time
import secrets
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ParticipantRole(Enum):
    HOST = "host"           # The person interviewing
    COLLABORATOR = "collaborator"  # Friend/mentor helping


class SessionStatus(Enum):
    WAITING = "waiting"     # Waiting for collaborator to join
    ACTIVE = "active"       # Both participants connected
    ENDED = "ended"         # Session ended


@dataclass
class Participant:
    id: str
    name: str
    role: ParticipantRole
    joined_at: float
    last_ping: float
    is_connected: bool = True


@dataclass
class CollaborationMessage:
    id: str
    sender_id: str
    sender_name: str
    text: str
    type: str  # suggestion, comment, alert, system
    timestamp: float
    is_private: bool = False  # Only host can see


@dataclass
class CollaborationSession:
    id: str
    join_code: str
    host_id: str
    participants: Dict[str, Participant]
    messages: List[CollaborationMessage]
    status: SessionStatus
    created_at: float
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    context: Dict = field(default_factory=dict)  # Interview context


class CollaborationManager:
    """
    Manages real-time collaboration sessions.

    Similar to LockedIn Duo but open-source and private.
    """

    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.join_code_map: Dict[str, str] = {}  # join_code -> session_id

    def create_session(self, host_name: str, interview_context: Dict = None) -> Dict:
        """Create a new collaboration session"""
        session_id = secrets.token_urlsafe(16)
        join_code = self._generate_join_code()

        host = Participant(
            id=secrets.token_urlsafe(8),
            name=host_name,
            role=ParticipantRole.HOST,
            joined_at=time.time(),
            last_ping=time.time(),
            is_connected=True
        )

        session = CollaborationSession(
            id=session_id,
            join_code=join_code,
            host_id=host.id,
            participants={host.id: host},
            messages=[],
            status=SessionStatus.WAITING,
            created_at=time.time(),
            context=interview_context or {}
        )

        self.sessions[session_id] = session
        self.join_code_map[join_code] = session_id

        return {
            "session_id": session_id,
            "join_code": join_code,
            "host_id": host.id,
            "status": "waiting",
            "share_url": f"ant://collaborate/{join_code}",
            "message": "Share the join code with your collaborator"
        }

    def join_session(self, join_code: str, collaborator_name: str) -> Optional[Dict]:
        """Join a collaboration session as collaborator"""
        session_id = self.join_code_map.get(join_code)
        if not session_id:
            return {"error": "Invalid join code"}

        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        if session.status == SessionStatus.ENDED:
            return {"error": "Session has ended"}

        # Check if already has a collaborator
        existing_collaborators = [
            p for p in session.participants.values()
            if p.role == ParticipantRole.COLLABORATOR
        ]

        if existing_collaborators:
            return {"error": "Session already has a collaborator"}

        # Add collaborator
        collaborator = Participant(
            id=secrets.token_urlsafe(8),
            name=collaborator_name,
            role=ParticipantRole.COLLABORATOR,
            joined_at=time.time(),
            last_ping=time.time(),
            is_connected=True
        )

        session.participants[collaborator.id] = collaborator
        session.status = SessionStatus.ACTIVE
        session.started_at = time.time()

        # Add system message
        self._add_system_message(session, f"{collaborator_name} joined the session")

        return {
            "session_id": session_id,
            "participant_id": collaborator.id,
            "role": "collaborator",
            "status": "active",
            "participants": [
                {"id": p.id, "name": p.name, "role": p.role.value}
                for p in session.participants.values()
            ]
        }

    def send_message(self, session_id: str, participant_id: str, text: str,
                     msg_type: str = "suggestion", is_private: bool = False) -> Dict:
        """Send a message in the collaboration session"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        participant = session.participants.get(participant_id)
        if not participant:
            return {"error": "Participant not found"}

        message = CollaborationMessage(
            id=secrets.token_urlsafe(8),
            sender_id=participant_id,
            sender_name=participant.name,
            text=text,
            type=msg_type,
            timestamp=time.time(),
            is_private=is_private and participant.role == ParticipantRole.COLLABORATOR
        )

        session.messages.append(message)

        return {
            "message_id": message.id,
            "sent": True,
            "timestamp": message.timestamp
        }

    def get_messages(self, session_id: str, participant_id: str,
                     since: float = 0) -> List[Dict]:
        """Get messages for a participant"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        participant = session.participants.get(participant_id)
        if not participant:
            return []

        # Update last ping
        participant.last_ping = time.time()

        # Filter messages
        messages = []
        for msg in session.messages:
            if msg.timestamp < since:
                continue

            # Hide private messages from host
            if msg.is_private and participant.role == ParticipantRole.HOST:
                continue

            messages.append({
                "id": msg.id,
                "sender": msg.sender_name,
                "text": msg.text,
                "type": msg.type,
                "timestamp": msg.timestamp,
                "is_private": msg.is_private
            })

        return messages

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get current session status"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.id,
            "status": session.status.value,
            "participants": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role.value,
                    "connected": p.is_connected
                }
                for p in session.participants.values()
            ],
            "created_at": session.created_at,
            "duration_seconds": time.time() - session.created_at
        }

    def end_session(self, session_id: str, participant_id: str) -> Dict:
        """End collaboration session"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Only host can end session
        if participant_id != session.host_id:
            return {"error": "Only host can end session"}

        session.status = SessionStatus.ENDED
        session.ended_at = time.time()

        self._add_system_message(session, "Session ended")

        # Cleanup
        del self.join_code_map[session.join_code]

        return {
            "status": "ended",
            "duration_seconds": session.ended_at - session.created_at,
            "total_messages": len(session.messages)
        }

    def _generate_join_code(self) -> str:
        """Generate a unique join code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in self.join_code_map:
                return code

    def _add_system_message(self, session: CollaborationSession, text: str):
        """Add a system message"""
        message = CollaborationMessage(
            id=secrets.token_urlsafe(8),
            sender_id="system",
            sender_name="System",
            text=text,
            type="system",
            timestamp=time.time()
        )
        session.messages.append(message)

    def cleanup_stale_sessions(self, max_age_hours: int = 24):
        """Remove old sessions"""
        now = time.time()
        stale_ids = []

        for session_id, session in self.sessions.items():
            age_hours = (now - session.created_at) / 3600
            if age_hours > max_age_hours:
                stale_ids.append(session_id)

        for session_id in stale_ids:
            session = self.sessions.get(session_id)
            if session:
                del self.join_code_map[session.join_code]
                del self.sessions[session_id]


# Global manager
collaboration_manager = CollaborationManager()


# API convenience functions
def create_collaboration_session(host_name: str, context: Dict = None) -> Dict:
    return collaboration_manager.create_session(host_name, context)


def join_collaboration(join_code: str, name: str) -> Dict:
    return collaboration_manager.join_session(join_code, name)


def send_collaboration_message(session_id: str, participant_id: str, text: str,
                               msg_type: str = "suggestion", is_private: bool = False) -> Dict:
    return collaboration_manager.send_message(session_id, participant_id, text, msg_type, is_private)


def get_collaboration_messages(session_id: str, participant_id: str, since: float = 0) -> List[Dict]:
    return collaboration_manager.get_messages(session_id, participant_id, since)


def get_collaboration_status(session_id: str) -> Optional[Dict]:
    return collaboration_manager.get_session_status(session_id)


def end_collaboration(session_id: str, participant_id: str) -> Dict:
    return collaboration_manager.end_session(session_id, participant_id)
