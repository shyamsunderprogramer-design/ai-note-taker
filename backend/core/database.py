"""
database.py - PostgreSQL/SQLite Database Layer for AI Note Taker
SQLAlchemy async ORM with connection pooling, JSONB support, migration utilities

T16: Database Migration (JSON -> PostgreSQL)
- SQLAlchemy models for all entities
- Async connection pooling
- Repository pattern for data access
- Migration utilities from JSON files
- Backup/restore endpoints
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

# Encryption support for data at rest
try:
    from security.encryption import (
        field_encryption, encrypt_string, decrypt_string,
        is_encryption_available, HAS_CRYPTOGRAPHY,
    )
    ENCRYPTION_ENABLED = HAS_CRYPTOGRAPHY
except ImportError:
    ENCRYPTION_ENABLED = False
    logging.getLogger("database").warning("[Database] Encryption module not available")

logger = logging.getLogger("database")

# Database configuration
# T16: Try PostgreSQL first, fall back to SQLite for development
DEFAULT_POSTGRES_URL = ""  # Must be set via DATABASE_URL env var in production

# SQLite path: use absolute path based on this file's location
_BACKEND_DIR = Path(__file__).resolve().parent  # backend/core/
_DATA_DIR = _BACKEND_DIR.parent / "data"  # backend/data/
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{_DATA_DIR / 'ainotetaker.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_POSTGRES_URL)
USE_SQLITE = os.getenv("USE_SQLITE", "").lower() == "true"
FORCE_SQLITE = os.getenv("FORCE_SQLITE", "true").lower() == "true"  # Default to SQLite until PostgreSQL is configured
CLOUD_MODE = os.getenv("CLOUD_MODE", "false").lower() == "true"

# In cloud mode, try PostgreSQL first; fall back to SQLite if connection fails
if CLOUD_MODE and DATABASE_URL and "postgresql" in DATABASE_URL:
    FORCE_SQLITE = False
    USE_SQLITE = False
    logger.info("[Database] Cloud mode: will attempt PostgreSQL at %s", re.sub(r'://[^@]+@', '://***@', DATABASE_URL))
elif CLOUD_MODE:
    # Cloud mode but no DATABASE_URL — use SQLite with persistent path
    FORCE_SQLITE = True
    USE_SQLITE = True
    DATABASE_URL = DEFAULT_SQLITE_URL
    logger.info("[Database] Cloud mode: no DATABASE_URL, using SQLite at %s", DATABASE_URL)

# Auto-detect: if DATABASE_URL contains sqlite, use it
if "sqlite" in DATABASE_URL.lower():
    USE_SQLITE = True

# Force SQLite for development (safer default)
if FORCE_SQLITE:
    USE_SQLITE = True
    DATABASE_URL = DEFAULT_SQLITE_URL
elif USE_SQLITE:
    DATABASE_URL = DEFAULT_SQLITE_URL

_redacted_url = re.sub(r'://[^@]+@', '://***@', DATABASE_URL) if DATABASE_URL else "(none)"
logger.info(f"[Database] Module loaded. URL: {_redacted_url}")

# Try importing SQLAlchemy
try:
    from sqlalchemy import (
        Column, String, DateTime, Boolean, Integer, Float,
        ForeignKey, Text, JSON, select, delete, text, func
    )
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase, relationship
    from sqlalchemy.ext.asyncio import AsyncEngine
    HAS_SQLALCHEMY = True
except ImportError as e:
    HAS_SQLALCHEMY = False
    logger.warning("[Database] SQLAlchemy not available: %s", str(e))

if HAS_SQLALCHEMY:
    class Base(DeclarativeBase):
        pass
else:
    Base = None


# ============================================================================
# MODEL CLASSES
# ============================================================================

class User(Base if Base else object):
    """User accounts and authentication"""
    __tablename__ = "users"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        username = Column(String(50), unique=True, nullable=False, index=True)
        email = Column(String(255), unique=True, nullable=False, index=True)
        hashed_password = Column(String(255), nullable=False)
        is_active = Column(Boolean, default=True)
        is_admin = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
        last_login = Column(DateTime, nullable=True)
        api_quota = Column(JSON, default=dict)
        display_name = Column(String(100), nullable=True)
        timezone = Column(String(50), default="UTC")

        # Relationships
        conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
        voice_models = relationship("VoiceModel", back_populates="user", cascade="all, delete-orphan")
        job_applications = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")
        documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self, include_sensitive=False):
        data = {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "username": getattr(self, 'username', None),
            "email": getattr(self, 'email', None),
            "is_active": getattr(self, 'is_active', True),
            "is_admin": getattr(self, 'is_admin', False),
            "created_at": getattr(self, 'created_at', None),
            "last_login": getattr(self, 'last_login', None),
            "display_name": getattr(self, 'display_name', None),
            "timezone": getattr(self, 'timezone', "UTC"),
        }
        if include_sensitive:
            data["api_quota"] = getattr(self, 'api_quota', {})
        return data


class Conversation(Base if Base else object):
    """Stored conversations with messages"""
    __tablename__ = "conversations"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        title = Column(String(255), nullable=True)
        messages = Column(JSON, default=list)
        meta = Column(JSON, default=dict)
        created_at = Column(DateTime, default=datetime.now(timezone.utc), index=True)
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
        message_count = Column(Integer, default=0)
        is_encrypted = Column(Boolean, default=False)

        # Relationships
        user = relationship("User", back_populates="conversations")

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "title": getattr(self, 'title', None),
            "messages": getattr(self, 'messages', []),
            "message_count": getattr(self, 'message_count', 0),
            "meta": getattr(self, 'meta', {}),
            "created_at": getattr(self, 'created_at', None),
            "updated_at": getattr(self, 'updated_at', None),
            "is_encrypted": getattr(self, 'is_encrypted', False),
        }


class VoiceModel(Base if Base else object):
    """Voice clone model metadata"""
    __tablename__ = "voice_models"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        name = Column(String(100), nullable=False)
        sample_count = Column(Integer, default=0)
        quality_score = Column(Float, default=0.0)
        status = Column(String(20), default="training")
        model_file = Column(String(500), nullable=True)
        source = Column(String(20), default="edge_tts")
        edge_voice = Column(String(50), default="")
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

        # Relationships
        user = relationship("User", back_populates="voice_models")

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "name": getattr(self, 'name', None),
            "sample_count": getattr(self, 'sample_count', 0),
            "quality_score": getattr(self, 'quality_score', 0.0),
            "status": getattr(self, 'status', 'training'),
            "source": getattr(self, 'source', 'edge_tts'),
            "edge_voice": getattr(self, 'edge_voice', ''),
            "created_at": getattr(self, 'created_at', None),
        }


class JobApplication(Base if Base else object):
    """Job application tracking"""
    __tablename__ = "job_applications"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        company = Column(String(100), nullable=False, index=True)
        role = Column(String(100), nullable=False, index=True)
        status = Column(String(30), default="saved", index=True)
        job_url = Column(String(500), nullable=True)
        notes = Column(JSON, default=list)
        interviews = Column(JSON, default=list)
        salary_range = Column(String(100), nullable=True)
        location = Column(String(100), nullable=True)
        remote_status = Column(String(20), nullable=True)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
        applied_at = Column(DateTime, nullable=True)

        # Relationships
        user = relationship("User", back_populates="job_applications")

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "company": getattr(self, 'company', None),
            "role": getattr(self, 'role', None),
            "status": getattr(self, 'status', 'saved'),
            "job_url": getattr(self, 'job_url', None),
            "notes": getattr(self, 'notes', []),
            "interviews": getattr(self, 'interviews', []),
            "salary_range": getattr(self, 'salary_range', None),
            "location": getattr(self, 'location', None),
            "remote_status": getattr(self, 'remote_status', None),
            "created_at": getattr(self, 'created_at', None),
            "updated_at": getattr(self, 'updated_at', None),
            "applied_at": getattr(self, 'applied_at', None),
        }


class InterviewSession(Base if Base else object):
    """Mock interview sessions"""
    __tablename__ = "interview_sessions"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        company = Column(String(100), nullable=False)
        role = Column(String(100), nullable=False)
        state = Column(String(20), default="idle")
        questions = Column(JSON, default=list)
        answers = Column(JSON, default=list)
        evaluations = Column(JSON, default=list)
        overall_score = Column(Float, nullable=True)
        started_at = Column(DateTime, default=datetime.now(timezone.utc))
        completed_at = Column(DateTime, nullable=True)
        duration_seconds = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "company": getattr(self, 'company', None),
            "role": getattr(self, 'role', None),
            "state": getattr(self, 'state', 'idle'),
            "questions": getattr(self, 'questions', []),
            "answers": getattr(self, 'answers', []),
            "evaluations": getattr(self, 'evaluations', []),
            "overall_score": getattr(self, 'overall_score', None),
            "started_at": getattr(self, 'started_at', None),
            "completed_at": getattr(self, 'completed_at', None),
            "duration_seconds": getattr(self, 'duration_seconds', None),
        }


class AnalyticsEvent(Base if Base else object):
    """Usage analytics events"""
    __tablename__ = "analytics_events"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
        event_type = Column(String(50), nullable=False, index=True)
        data = Column(JSON, default=dict)
        session_id = Column(String(100), nullable=True, index=True)
        ip_address = Column(String(45), nullable=True)
        user_agent = Column(String(500), nullable=True)
        timestamp = Column(DateTime, default=datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "event_type": getattr(self, 'event_type', None),
            "data": getattr(self, 'data', {}),
            "session_id": getattr(self, 'session_id', None),
            "timestamp": getattr(self, 'timestamp', None),
        }


class UserAPIKey(Base if Base else object):
    """Encrypted API keys for BYOK"""
    __tablename__ = "user_api_keys"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
        openai_key_encrypted = Column(Text, nullable=True)
        anthropic_key_encrypted = Column(Text, nullable=True)
        google_key_encrypted = Column(Text, nullable=True)
        deepseek_key_encrypted = Column(Text, nullable=True)
        grok_key_encrypted = Column(Text, nullable=True)
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "has_openai": bool(getattr(self, 'openai_key_encrypted', None)),
            "has_anthropic": bool(getattr(self, 'anthropic_key_encrypted', None)),
            "has_google": bool(getattr(self, 'google_key_encrypted', None)),
            "has_deepseek": bool(getattr(self, 'deepseek_key_encrypted', None)),
            "has_grok": bool(getattr(self, 'grok_key_encrypted', None)),
            "updated_at": getattr(self, 'updated_at', None),
        }


class Document(Base if Base else object):
    """RAG documents with embeddings"""
    __tablename__ = "documents"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        filename = Column(String(255), nullable=False)
        content = Column(Text, nullable=True)
        chunks = Column(JSON, default=list)
        embeddings = Column(JSON, nullable=True)
        processing_status = Column(String(20), default="pending")
        file_size = Column(Integer, nullable=True)
        mime_type = Column(String(100), nullable=True)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

        # Relationships
        user = relationship("User", back_populates="documents")

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "filename": getattr(self, 'filename', None),
            "status": getattr(self, 'processing_status', 'pending'),
            "file_size": getattr(self, 'file_size', None),
            "mime_type": getattr(self, 'mime_type', None),
            "created_at": getattr(self, 'created_at', None),
            "updated_at": getattr(self, 'updated_at', None),
        }


class AgentSession(Base if Base else object):
    """Unified agent session — persists across all agent types."""
    __tablename__ = "agent_sessions"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        session_type = Column(String(30), nullable=False, index=True)  # "interview", "sales_call", "meeting"
        state = Column(String(20), default="idle")
        company = Column(String(100), nullable=True)
        role = Column(String(100), nullable=True)
        stage = Column(String(50), nullable=True)
        active_agents = Column(JSON, default=list)   # ["interview_coach", "meeting", "sales_coach"]
        config = Column(JSON, default=dict)          # provider, temperature, user_profile, etc.
        transcript_buffer = Column(JSON, default=list)  # last N segments
        agent_states = Column(JSON, default=dict)    # per-agent state
        suggestions = Column(JSON, default=list)     # all suggestions this session
        entities = Column(JSON, default=dict)        # extracted entities cache
        started_at = Column(DateTime, default=datetime.now(timezone.utc))
        ended_at = Column(DateTime, nullable=True)
        duration_seconds = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "session_type": getattr(self, 'session_type', 'meeting'),
            "state": getattr(self, 'state', 'idle'),
            "company": getattr(self, 'company', None),
            "role": getattr(self, 'role', None),
            "stage": getattr(self, 'stage', None),
            "active_agents": getattr(self, 'active_agents', []),
            "config": getattr(self, 'config', {}),
            "transcript_buffer": getattr(self, 'transcript_buffer', []),
            "agent_states": getattr(self, 'agent_states', {}),
            "suggestions": getattr(self, 'suggestions', []),
            "entities": getattr(self, 'entities', {}),
            "started_at": getattr(self, 'started_at', None),
            "ended_at": getattr(self, 'ended_at', None),
            "duration_seconds": getattr(self, 'duration_seconds', None),
        }


class CRMConfig(Base if Base else object):
    """CRM integration configuration"""
    __tablename__ = "crm_configs"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
        enabled = Column(Boolean, default=False)
        provider = Column(String(20), default="")
        api_key_encrypted = Column(Text, nullable=True)
        instance_url = Column(String(500), nullable=True)
        sync_frequency = Column(String(20), default="daily")
        last_sync_at = Column(DateTime, nullable=True)
        sync_errors = Column(JSON, default=list)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "enabled": getattr(self, 'enabled', False),
            "provider": getattr(self, 'provider', None),
            "instance_url": getattr(self, 'instance_url', None),
            "sync_frequency": getattr(self, 'sync_frequency', 'daily'),
            "last_sync_at": getattr(self, 'last_sync_at', None),
            "created_at": getattr(self, 'created_at', None),
            "updated_at": getattr(self, 'updated_at', None),
        }


class IntegrationConfig(Base if Base else object):
    """Generic integration configuration — one row per user per integration type."""
    __tablename__ = "integration_configs"
    __table_args__ = (
        {"extend_existing": True},
    )

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        integration_type = Column(String(30), nullable=False, index=True)
        enabled = Column(Boolean, default=False)
        config = Column(JSON, default=dict)
        secrets_encrypted = Column(Text, nullable=True)
        last_sync_at = Column(DateTime, nullable=True)
        sync_errors = Column(JSON, default=list)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self, include_secrets=False):
        d = {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "integration_type": getattr(self, 'integration_type', None),
            "enabled": getattr(self, 'enabled', False),
            "config": getattr(self, 'config', {}) or {},
            "last_sync_at": getattr(self, 'last_sync_at', None),
            "sync_errors": getattr(self, 'sync_errors', []) or [],
            "created_at": getattr(self, 'created_at', None),
            "updated_at": getattr(self, 'updated_at', None),
        }
        if include_secrets:
            d["secrets"] = self._decrypt_secrets()
        return d

    def _decrypt_secrets(self):
        raw = getattr(self, 'secrets_encrypted', None)
        if not raw:
            return {}
        try:
            if raw.startswith("plain:"):
                return json.loads(raw[6:])
            if ENCRYPTION_ENABLED:
                decrypted = decrypt_string(raw)
                if decrypted:
                    return json.loads(decrypted)
        except Exception:
            pass
        return {}


class Team(Base if Base else object):
    """Team workspaces for collaboration."""
    __tablename__ = "teams"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name = Column(String(100), nullable=False)
        description = Column(Text, default="")
        created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "name": getattr(self, 'name', ""),
            "description": getattr(self, 'description', ""),
            "created_by": str(self.created_by) if hasattr(self, 'created_by') else None,
            "created_at": getattr(self, 'created_at', None),
        }


class TeamMember(Base if Base else object):
    """Team membership with roles."""
    __tablename__ = "team_members"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        team_id = Column(PGUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
        role = Column(String(20), default="member")
        joined_at = Column(DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "team_id": str(self.team_id) if hasattr(self, 'team_id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "role": getattr(self, 'role', "member"),
            "joined_at": getattr(self, 'joined_at', None),
        }


class AuditLog(Base if Base else object):
    """Audit log for security events"""
    __tablename__ = "audit_logs"

    if HAS_SQLALCHEMY:
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
        action = Column(String(50), nullable=False, index=True)
        resource_type = Column(String(50), nullable=False)
        resource_id = Column(String(100), nullable=True)
        details = Column(JSON, default=dict)
        ip_address = Column(String(45), nullable=True)
        user_agent = Column(String(500), nullable=True)
        success = Column(Boolean, default=True)
        error_message = Column(Text, nullable=True)
        timestamp = Column(DateTime, default=datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": str(self.id) if hasattr(self, 'id') else None,
            "user_id": str(self.user_id) if hasattr(self, 'user_id') else None,
            "action": getattr(self, 'action', None),
            "resource_type": getattr(self, 'resource_type', None),
            "resource_id": getattr(self, 'resource_id', None),
            "details": getattr(self, 'details', {}),
            "success": getattr(self, 'success', True),
            "timestamp": getattr(self, 'timestamp', None),
        }


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self):
        self.engine = None
        self.session_maker = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database engine and create tables"""
        if self._initialized or not HAS_SQLALCHEMY:
            if not HAS_SQLALCHEMY:
                logger.warning("[Database] SQLAlchemy not available, using JSON fallback")
            return

        try:
            # Dispose of any previous engine (e.g. from a failed PostgreSQL attempt)
            if self.engine:
                try:
                    await self.engine.dispose()
                except Exception:
                    pass
                self.engine = None
                self.session_maker = None

            # Build the effective database URL for this connection
            _db_url = DATABASE_URL

            # Ensure data directory exists for SQLite
            _is_sqlite = "sqlite" in _db_url.lower()
            if _is_sqlite:
                _db_path = _db_url.split("///")[-1] if ":///" in _db_url else None
                if _db_path:
                    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

            # Build connection args for cloud databases
            # Neon requires SSL — pass as SSLContext via connect_args
            connect_args = {}
            if "postgresql" in _db_url and "sqlite" not in _db_url:
                # Remove sslmode from URL if present — asyncpg doesn't use it in URL
                if "sslmode=" in _db_url:
                    _db_url = _db_url.split("?sslmode=")[0]
                    if _db_url.endswith("?"):
                        _db_url = _db_url[:-1]
                try:
                    import ssl as _ssl
                    _ssl_ctx = _ssl.create_default_context()
                    _ssl_ctx.check_hostname = False
                    _ssl_ctx.verify_mode = _ssl.CERT_NONE
                    connect_args["ssl"] = _ssl_ctx
                except Exception:
                    pass

            # Cloud mode: smaller pool to fit in 512MB RAM
            _pool_size = 2 if os.getenv("CLOUD_MODE", "false").lower() == "true" else 10
            _max_overflow = 2 if _pool_size == 2 else 20

            # SQLite doesn't support pool_size, max_overflow, or pool_pre_ping
            _engine_kwargs = {
                "echo": False,
            }
            if not _is_sqlite:
                _engine_kwargs["pool_size"] = _pool_size
                _engine_kwargs["max_overflow"] = _max_overflow
                _engine_kwargs["pool_timeout"] = 30
                _engine_kwargs["pool_pre_ping"] = True
                if connect_args:
                    _engine_kwargs["connect_args"] = connect_args

            logger.info("[Database] Connecting to: %s (SQLite=%s)", re.sub(r'://[^@]+@', '://***@', _db_url) if _db_url else "(none)", _is_sqlite)

            self.engine = create_async_engine(
                _db_url,
                **_engine_kwargs,
            )

            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True
            logger.info("[Database] Initialized successfully (%s)", "SQLite" if _is_sqlite else "PostgreSQL")

        except Exception as e:
            logger.error("[Database] Failed to initialize: %s", str(e))
            # Clean up partially created engine
            if self.engine:
                try:
                    await self.engine.dispose()
                except Exception:
                    pass
                self.engine = None
                self.session_maker = None
            raise

    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("[Database] Connections closed")

    async def health_check(self) -> bool:
        """Check database connectivity"""
        if not self.engine:
            logger.error("[Database] Health check: engine is None, database not initialized")
            return False
        try:
            async with self.session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error("[Database] Health check failed: %s", str(e))
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.engine or not self.session_maker:
            return {"error": "Database not initialized"}

        stats = {}
        try:
            async with self.session_maker() as session:
                # Count users
                result = await session.execute(select(func.count()).select_from(User))
                stats["users"] = result.scalar()

                # Count conversations
                result = await session.execute(select(func.count()).select_from(Conversation))
                stats["conversations"] = result.scalar()

                # Count voice models
                result = await session.execute(select(func.count()).select_from(VoiceModel))
                stats["voice_models"] = result.scalar()

                # Count job applications
                result = await session.execute(select(func.count()).select_from(JobApplication))
                stats["job_applications"] = result.scalar()

                # Count documents
                result = await session.execute(select(func.count()).select_from(Document))
                stats["documents"] = result.scalar()

                # Count analytics events
                result = await session.execute(select(func.count()).select_from(AnalyticsEvent))
                stats["analytics_events"] = result.scalar()

            return stats
        except Exception as e:
            logger.error("[Database] Failed to get stats: %s", str(e))
            return {"error": "An internal error occurred"}

    async def get_session(self):
        """Get a database session"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        return self.session_maker()


# Global instance
db_manager = DatabaseManager()


async def init_database():
    """Initialize the database"""
    await db_manager.initialize()


async def close_database():
    """Close database connections"""
    await db_manager.close()


# ============================================================================
# REPOSITORY CLASSES
# ============================================================================

class UserRepository:
    """User data access layer"""

    @staticmethod
    async def create(username: str, email: str, hashed_password: str, is_admin: bool = False, **kwargs) -> Optional[User]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                user = User(
                    username=username,
                    email=email,
                    hashed_password=hashed_password,
                    is_admin=is_admin,
                    **kwargs
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return user
        except Exception as e:
            logger.error("[UserRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_id(user_id: str) -> Optional[User]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[UserRepository] Get by ID failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_username(username: str) -> Optional[User]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(select(User).where(User.username == username))
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[UserRepository] Get by username failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(select(User).where(User.email == email))
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[UserRepository] Get by email failed: %s", str(e))
            return None

    @staticmethod
    async def update(user_id: str, **kwargs) -> Optional[User]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    for key, value in kwargs.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                    user.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(user)
                return user
        except Exception as e:
            logger.error("[UserRepository] Update failed: %s", str(e))
            return None

    @staticmethod
    async def delete(user_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(delete(User).where(User.id == uuid.UUID(user_id)))
                await db.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error("[UserRepository] Delete failed: %s", str(e))
            return False

    @staticmethod
    async def list_all(limit: int = 100, offset: int = 0) -> List[User]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error("[UserRepository] List failed: %s", str(e))
            return []


class ConversationRepository:
    """Conversation data access layer with encryption at rest"""

    # Fields to encrypt when ENCRYPTION_ENABLED
    _encrypted_fields = ["messages"]

    @staticmethod
    def _encrypt_messages(messages: List[Dict]) -> tuple:
        """Encrypt messages list. Returns (encrypted_json_str, is_encrypted)."""
        if not ENCRYPTION_ENABLED or not messages:
            return messages, False
        try:
            plain = json.dumps(messages)
            encrypted = encrypt_string(plain)
            if encrypted:
                return encrypted, True
        except Exception as e:
            logger.warning("[ConversationRepository] Encryption failed, storing plaintext: %s", str(e))
        return messages, False

    @staticmethod
    def _decrypt_messages(conv: Conversation) -> Conversation:
        """Decrypt messages if encrypted. Modifies conv in place."""
        if not ENCRYPTION_ENABLED or not conv or not getattr(conv, 'is_encrypted', False):
            return conv
        try:
            raw = getattr(conv, 'messages', None)
            if isinstance(raw, str) and raw:
                decrypted = decrypt_string(raw)
                if decrypted:
                    conv.messages = json.loads(decrypted)
                    conv.is_encrypted = False  # Decrypted for use
        except Exception as e:
            logger.warning("[ConversationRepository] Decryption failed: %s", str(e))
        return conv

    @staticmethod
    async def create(user_id: str, title: str = None, messages: List[Dict] = None, **kwargs) -> Optional[Conversation]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                encrypted_messages = messages or []
                is_encrypted = False
                if encrypted_messages and ENCRYPTION_ENABLED:
                    encrypted_messages, is_encrypted = ConversationRepository._encrypt_messages(encrypted_messages)

                conv = Conversation(
                    user_id=uuid.UUID(user_id),
                    title=title,
                    messages=encrypted_messages,
                    message_count=len(messages) if messages else 0,
                    is_encrypted=is_encrypted,
                    **kwargs
                )
                db.add(conv)
                await db.commit()
                await db.refresh(conv)
                return conv
        except Exception as e:
            logger.error("[ConversationRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_id(conversation_id: str) -> Optional[Conversation]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
                )
                conv = result.scalar_one_or_none()
                return ConversationRepository._decrypt_messages(conv) if conv else None
        except Exception as e:
            logger.error("[ConversationRepository] Get by ID failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str, limit: int = 100, offset: int = 0) -> List[Conversation]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Conversation)
                    .where(Conversation.user_id == uuid.UUID(user_id))
                    .order_by(Conversation.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                convs = result.scalars().all()
                return [ConversationRepository._decrypt_messages(c) for c in convs]
        except Exception as e:
            logger.error("[ConversationRepository] Get by user failed: %s", str(e))
            return []

    @staticmethod
    async def update_messages(conversation_id: str, messages: List[Dict]) -> Optional[Conversation]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
                )
                conv = result.scalar_one_or_none()
                if conv:
                    encrypted_messages = messages
                    is_encrypted = False
                    if messages and ENCRYPTION_ENABLED:
                        encrypted_messages, is_encrypted = ConversationRepository._encrypt_messages(messages)

                    conv.messages = encrypted_messages
                    conv.message_count = len(messages) if messages else 0
                    conv.is_encrypted = is_encrypted
                    conv.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(conv)
                return conv
        except Exception as e:
            logger.error("[ConversationRepository] Update messages failed: %s", str(e))
            return None

    @staticmethod
    async def delete(conversation_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
                )
                await db.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error("[ConversationRepository] Delete failed: %s", str(e))
            return False

    @staticmethod
    async def delete_by_user(user_id: str) -> int:
        """Delete all conversations for a user (GDPR right to be forgotten)."""
        if not HAS_SQLALCHEMY:
            return 0
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(Conversation).where(Conversation.user_id == uuid.UUID(user_id))
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error("[ConversationRepository] Delete by user failed: %s", str(e))
            return 0

    @staticmethod
    async def search(user_id: str, query: str) -> List[Conversation]:
        """Search conversations by content (PostgreSQL only)"""
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                # Simple search - in production would use full-text search
                result = await db.execute(
                    select(Conversation)
                    .where(Conversation.user_id == uuid.UUID(user_id))
                    .where(Conversation.title.ilike(f"%{query}%"))
                    .order_by(Conversation.created_at.desc())
                )
                return result.scalars().all()
        except Exception as e:
            logger.error("[ConversationRepository] Search failed: %s", str(e))
            return []


class VoiceModelRepository:
    """Voice model data access layer"""

    @staticmethod
    async def create(user_id: str, name: str, **kwargs) -> Optional[VoiceModel]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                model = VoiceModel(user_id=uuid.UUID(user_id), name=name, **kwargs)
                db.add(model)
                await db.commit()
                await db.refresh(model)
                return model
        except Exception as e:
            logger.error("[VoiceModelRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_id(model_id: str) -> Optional[VoiceModel]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(VoiceModel).where(VoiceModel.id == uuid.UUID(model_id))
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[VoiceModelRepository] Get by ID failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str, limit: int = 100) -> List[VoiceModel]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(VoiceModel)
                    .where(VoiceModel.user_id == uuid.UUID(user_id))
                    .order_by(VoiceModel.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error("[VoiceModelRepository] Get by user failed: %s", str(e))
            return []

    @staticmethod
    async def update_status(model_id: str, status: str, **kwargs) -> Optional[VoiceModel]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(VoiceModel).where(VoiceModel.id == uuid.UUID(model_id))
                )
                model = result.scalar_one_or_none()
                if model:
                    model.status = status
                    for key, value in kwargs.items():
                        if hasattr(model, key):
                            setattr(model, key, value)
                    model.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(model)
                return model
        except Exception as e:
            logger.error("[VoiceModelRepository] Update status failed: %s", str(e))
            return None

    @staticmethod
    async def delete(model_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(VoiceModel).where(VoiceModel.id == uuid.UUID(model_id))
                )
                await db.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error("[VoiceModelRepository] Delete failed: %s", str(e))
            return False

    @staticmethod
    async def delete_by_user(user_id: str) -> int:
        """Delete all voice models for a user (GDPR)."""
        if not HAS_SQLALCHEMY:
            return 0
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(VoiceModel).where(VoiceModel.user_id == uuid.UUID(user_id))
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error("[VoiceModelRepository] Delete by user failed: %s", str(e))
            return 0


class JobApplicationRepository:
    """Job application data access layer"""

    @staticmethod
    async def create(user_id: str, company: str, role: str, **kwargs) -> Optional[JobApplication]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                app = JobApplication(
                    user_id=uuid.UUID(user_id),
                    company=company,
                    role=role,
                    **kwargs
                )
                db.add(app)
                await db.commit()
                await db.refresh(app)
                return app
        except Exception as e:
            logger.error("[JobApplicationRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_id(app_id: str) -> Optional[JobApplication]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(JobApplication).where(JobApplication.id == uuid.UUID(app_id))
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[JobApplicationRepository] Get by ID failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str, status: str = None, limit: int = 100, offset: int = 0) -> List[JobApplication]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                query = select(JobApplication).where(JobApplication.user_id == uuid.UUID(user_id))
                if status:
                    query = query.where(JobApplication.status == status)
                query = query.order_by(JobApplication.created_at.desc()).limit(limit).offset(offset)
                result = await db.execute(query)
                return result.scalars().all()
        except Exception as e:
            logger.error("[JobApplicationRepository] Get by user failed: %s", str(e))
            return []

    @staticmethod
    async def update_status(app_id: str, status: str, **kwargs) -> Optional[JobApplication]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(JobApplication).where(JobApplication.id == uuid.UUID(app_id))
                )
                app = result.scalar_one_or_none()
                if app:
                    app.status = status
                    for key, value in kwargs.items():
                        if hasattr(app, key):
                            setattr(app, key, value)
                    app.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(app)
                return app
        except Exception as e:
            logger.error("[JobApplicationRepository] Update status failed: %s", str(e))
            return None

    @staticmethod
    async def delete(app_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(JobApplication).where(JobApplication.id == uuid.UUID(app_id))
                )
                await db.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error("[JobApplicationRepository] Delete failed: %s", str(e))
            return False

    @staticmethod
    async def delete_by_user(user_id: str) -> int:
        """Delete all job applications for a user (GDPR)."""
        if not HAS_SQLALCHEMY:
            return 0
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(JobApplication).where(JobApplication.user_id == uuid.UUID(user_id))
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error("[JobApplicationRepository] Delete by user failed: %s", str(e))
            return 0


class DocumentRepository:
    """Document data access layer"""

    @staticmethod
    async def create(user_id: str, filename: str, **kwargs) -> Optional[Document]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                doc = Document(user_id=uuid.UUID(user_id), filename=filename, **kwargs)
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                return doc
        except Exception as e:
            logger.error("[DocumentRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str, limit: int = 100) -> List[Document]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Document)
                    .where(Document.user_id == uuid.UUID(user_id))
                    .order_by(Document.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error("[DocumentRepository] Get by user failed: %s", str(e))
            return []

    @staticmethod
    async def update_status(doc_id: str, status: str, **kwargs) -> Optional[Document]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Document).where(Document.id == uuid.UUID(doc_id))
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.processing_status = status
                    for key, value in kwargs.items():
                        if hasattr(doc, key):
                            setattr(doc, key, value)
                    doc.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(doc)
                return doc
        except Exception as e:
            logger.error("[DocumentRepository] Update status failed: %s", str(e))
            return None

    @staticmethod
    async def delete_by_user(user_id: str) -> int:
        """Delete all documents for a user (GDPR)."""
        if not HAS_SQLALCHEMY:
            return 0
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(Document).where(Document.user_id == uuid.UUID(user_id))
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error("[DocumentRepository] Delete by user failed: %s", str(e))
            return 0


class AnalyticsRepository:
    """Analytics data access layer"""

    @staticmethod
    async def create_event(user_id: str = None, event_type: str = None, data: Dict = None, **kwargs) -> Optional[AnalyticsEvent]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                event = AnalyticsEvent(
                    user_id=uuid.UUID(user_id) if user_id else None,
                    event_type=event_type,
                    data=data or {},
                    **kwargs
                )
                db.add(event)
                await db.commit()
                await db.refresh(event)
                return event
        except Exception as e:
            logger.error("[AnalyticsRepository] Create event failed: %s", str(e))
            return None

    @staticmethod
    async def get_events(user_id: str = None, event_type: str = None, limit: int = 1000, offset: int = 0) -> List[AnalyticsEvent]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                query = select(AnalyticsEvent)
                if user_id:
                    query = query.where(AnalyticsEvent.user_id == uuid.UUID(user_id))
                if event_type:
                    query = query.where(AnalyticsEvent.event_type == event_type)
                query = query.order_by(AnalyticsEvent.timestamp.desc()).limit(limit).offset(offset)
                result = await db.execute(query)
                return result.scalars().all()
        except Exception as e:
            logger.error("[AnalyticsRepository] Get events failed: %s", str(e))
            return []

    @staticmethod
    async def get_by_user(user_id: str, limit: int = 10000) -> List[AnalyticsEvent]:
        """Get all analytics events for a user (GDPR export)."""
        return await AnalyticsRepository.get_events(user_id=user_id, limit=limit)

    @staticmethod
    async def delete_by_user(user_id: str) -> int:
        """Delete all analytics events for a user (GDPR)."""
        if not HAS_SQLALCHEMY:
            return 0
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    delete(AnalyticsEvent).where(AnalyticsEvent.user_id == uuid.UUID(user_id))
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error("[AnalyticsRepository] Delete by user failed: %s", str(e))
            return 0

    @staticmethod
    async def get_event_counts_by_type(start_date: datetime = None, end_date: datetime = None) -> Dict[str, int]:
        """Get event counts grouped by type"""
        if not HAS_SQLALCHEMY:
            return {}
        try:
            async with db_manager.session_maker() as db:
                query = select(AnalyticsEvent.event_type, func.count()).group_by(AnalyticsEvent.event_type)
                if start_date:
                    query = query.where(AnalyticsEvent.timestamp >= start_date)
                if end_date:
                    query = query.where(AnalyticsEvent.timestamp <= end_date)
                result = await db.execute(query)
                return {row[0]: row[1] for row in result.all()}
        except Exception as e:
            logger.error("[AnalyticsRepository] Get counts failed: %s", str(e))
            return {}


class AuditLogRepository:
    """Audit log data access layer"""

    @staticmethod
    async def create(user_id: str = None, action: str = None, resource_type: str = None, **kwargs) -> Optional[AuditLog]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                log = AuditLog(
                    user_id=uuid.UUID(user_id) if user_id else None,
                    action=action,
                    resource_type=resource_type,
                    **kwargs
                )
                db.add(log)
                await db.commit()
                await db.refresh(log)
                return log
        except Exception as e:
            logger.error("[AuditLogRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_logs(user_id: str = None, action: str = None, limit: int = 1000) -> List[AuditLog]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                query = select(AuditLog)
                if user_id:
                    query = query.where(AuditLog.user_id == uuid.UUID(user_id))
                if action:
                    query = query.where(AuditLog.action == action)
                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                result = await db.execute(query)
                return result.scalars().all()
        except Exception as e:
            logger.error("[AuditLogRepository] Get logs failed: %s", str(e))
            return []


class UserAPIKeyRepository:
    """API key data access layer with encryption support (T17)"""

    @staticmethod
    def _get_encryption():
        """Lazy load encryption manager"""
        try:
            from security import encrypt_api_key, decrypt_api_key
            return encrypt_api_key, decrypt_api_key
        except ImportError:
            return None, None

    @staticmethod
    async def create_or_update(user_id: str, **keys) -> Optional[UserAPIKey]:
        """Create or update API keys with encryption"""
        if not HAS_SQLALCHEMY:
            return None

        encrypt_fn, _ = UserAPIKeyRepository._get_encryption()

        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(UserAPIKey).where(UserAPIKey.user_id == uuid.UUID(user_id))
                )
                api_keys = result.scalar_one_or_none()

                # Encrypt keys before storing
                encrypted_keys = {}
                for key_name, key_value in keys.items():
                    if key_value and key_name.endswith('_key'):
                        col_name = key_name.replace('_key', '_key_encrypted')
                        if encrypt_fn:
                            encrypted_keys[col_name] = encrypt_fn(key_value)
                        else:
                            # Store with prefix if encryption unavailable
                            encrypted_keys[col_name] = f"plain:{key_value}"

                if api_keys:
                    # Update existing
                    for col, val in encrypted_keys.items():
                        setattr(api_keys, col, val)
                    api_keys.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new
                    api_keys = UserAPIKey(user_id=uuid.UUID(user_id), **encrypted_keys)
                    db.add(api_keys)

                await db.commit()
                await db.refresh(api_keys)
                return api_keys
        except Exception as e:
            logger.error("[UserAPIKeyRepository] Create/update failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str) -> Optional[Dict[str, str]]:
        """Get decrypted API keys for user"""
        if not HAS_SQLALCHEMY:
            return None

        _, decrypt_fn = UserAPIKeyRepository._get_encryption()

        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(UserAPIKey).where(UserAPIKey.user_id == uuid.UUID(user_id))
                )
                api_keys = result.scalar_one_or_none()

                if not api_keys:
                    return None

                # Decrypt keys
                decrypted = {}
                key_map = {
                    'openai_key_encrypted': 'openai',
                    'anthropic_key_encrypted': 'anthropic',
                    'google_key_encrypted': 'google',
                    'deepseek_key_encrypted': 'deepseek',
                    'grok_key_encrypted': 'grok',
                }

                for col, provider in key_map.items():
                    encrypted = getattr(api_keys, col, None)
                    if encrypted:
                        if encrypted.startswith("enc:") and decrypt_fn:
                            decrypted[provider] = decrypt_fn(encrypted)
                        elif encrypted.startswith("plain:"):
                            decrypted[provider] = encrypted[6:]
                        else:
                            # Legacy or other format - try decrypt
                            if decrypt_fn:
                                try:
                                    decrypted[provider] = decrypt_fn(encrypted)
                                except:
                                    decrypted[provider] = encrypted
                            else:
                                decrypted[provider] = encrypted

                return decrypted
        except Exception as e:
            logger.error("[UserAPIKeyRepository] Get by user failed: %s", str(e))
            return None

    @staticmethod
    async def delete_key(user_id: str, provider: str) -> bool:
        """Delete a specific API key"""
        if not HAS_SQLALCHEMY:
            return False

        col_map = {
            'openai': 'openai_key_encrypted',
            'anthropic': 'anthropic_key_encrypted',
            'google': 'google_key_encrypted',
            'deepseek': 'deepseek_key_encrypted',
            'grok': 'grok_key_encrypted',
        }

        if provider not in col_map:
            return False

        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(UserAPIKey).where(UserAPIKey.user_id == uuid.UUID(user_id))
                )
                api_keys = result.scalar_one_or_none()

                if api_keys:
                    setattr(api_keys, col_map[provider], None)
                    api_keys.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    return True
                return False
        except Exception as e:
            logger.error("[UserAPIKeyRepository] Delete failed: %s", str(e))
            return False


class IntegrationConfigRepository:
    """Generic integration config data access with encryption support."""

    @staticmethod
    async def upsert(user_id: str, integration_type: str, config: dict = None, secrets: dict = None, enabled: bool = True) -> Optional[IntegrationConfig]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(IntegrationConfig).where(
                        IntegrationConfig.user_id == uuid.UUID(user_id),
                        IntegrationConfig.integration_type == integration_type,
                    )
                )
                record = result.scalar_one_or_none()

                if record:
                    if config is not None:
                        record.config = config
                    if secrets is not None:
                        record.secrets_encrypted = IntegrationConfigRepository._encrypt_secrets(secrets)
                    record.enabled = enabled
                    record.updated_at = datetime.now(timezone.utc)
                else:
                    secrets_str = IntegrationConfigRepository._encrypt_secrets(secrets) if secrets else None
                    record = IntegrationConfig(
                        user_id=uuid.UUID(user_id),
                        integration_type=integration_type,
                        enabled=enabled,
                        config=config or {},
                        secrets_encrypted=secrets_str,
                    )
                    db.add(record)

                await db.commit()
                await db.refresh(record)
                return record
        except Exception as e:
            logger.error("[IntegrationConfigRepository] Upsert failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user_and_type(user_id: str, integration_type: str) -> Optional[IntegrationConfig]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(IntegrationConfig).where(
                        IntegrationConfig.user_id == uuid.UUID(user_id),
                        IntegrationConfig.integration_type == integration_type,
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[IntegrationConfigRepository] Get failed: %s", str(e))
            return None

    @staticmethod
    async def get_all_by_user(user_id: str) -> List[IntegrationConfig]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(IntegrationConfig).where(IntegrationConfig.user_id == uuid.UUID(user_id))
                )
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[IntegrationConfigRepository] Get all failed: %s", str(e))
            return []

    @staticmethod
    async def delete(user_id: str, integration_type: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(IntegrationConfig).where(
                        IntegrationConfig.user_id == uuid.UUID(user_id),
                        IntegrationConfig.integration_type == integration_type,
                    )
                )
                record = result.scalar_one_or_none()
                if record:
                    await db.delete(record)
                    await db.commit()
                    return True
                return False
        except Exception as e:
            logger.error("[IntegrationConfigRepository] Delete failed: %s", str(e))
            return False

    @staticmethod
    def _encrypt_secrets(secrets_dict: dict) -> str:
        raw = json.dumps(secrets_dict)
        if ENCRYPTION_ENABLED:
            try:
                return encrypt_string(raw)
            except Exception:
                pass
        return f"plain:{raw}"

    @staticmethod
    def decrypt_secrets_for_record(record: IntegrationConfig) -> dict:
        if not record:
            return {}
        return record._decrypt_secrets()


class TeamRepository:
    """Team workspace data access."""

    @staticmethod
    async def create(name: str, description: str, created_by: str) -> Optional[Team]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                team = Team(
                    name=name,
                    description=description,
                    created_by=uuid.UUID(created_by),
                )
                db.add(team)
                await db.commit()
                await db.refresh(team)
                # Auto-add creator as admin
                member = TeamMember(
                    team_id=team.id,
                    user_id=uuid.UUID(created_by),
                    role="admin",
                )
                db.add(member)
                await db.commit()
                return team
        except Exception as e:
            logger.error("[TeamRepository] Create failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_id(team_id: str) -> Optional[Team]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Team).where(Team.id == uuid.UUID(team_id))
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[TeamRepository] Get by ID failed: %s", str(e))
            return None

    @staticmethod
    async def get_by_user(user_id: str) -> List[Team]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Team).join(TeamMember, TeamMember.team_id == Team.id).where(
                        TeamMember.user_id == uuid.UUID(user_id)
                    )
                )
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[TeamRepository] Get by user failed: %s", str(e))
            return []

    @staticmethod
    async def delete_team(team_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(Team).where(Team.id == uuid.UUID(team_id))
                )
                team = result.scalar_one_or_none()
                if team:
                    await db.delete(team)
                    await db.commit()
                    return True
                return False
        except Exception as e:
            logger.error("[TeamRepository] Delete failed: %s", str(e))
            return False


class TeamMemberRepository:
    """Team membership data access."""

    @staticmethod
    async def add(team_id: str, user_id: str, role: str = "member") -> Optional[TeamMember]:
        if not HAS_SQLALCHEMY:
            return None
        try:
            async with db_manager.session_maker() as db:
                member = TeamMember(
                    team_id=uuid.UUID(team_id),
                    user_id=uuid.UUID(user_id),
                    role=role,
                )
                db.add(member)
                await db.commit()
                await db.refresh(member)
                return member
        except Exception as e:
            logger.error("[TeamMemberRepository] Add failed: %s", str(e))
            return None

    @staticmethod
    async def get_members(team_id: str) -> List[TeamMember]:
        if not HAS_SQLALCHEMY:
            return []
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(TeamMember).where(TeamMember.team_id == uuid.UUID(team_id))
                )
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[TeamMemberRepository] Get members failed: %s", str(e))
            return []

    @staticmethod
    async def remove(team_id: str, user_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == uuid.UUID(team_id),
                        TeamMember.user_id == uuid.UUID(user_id),
                    )
                )
                member = result.scalar_one_or_none()
                if member:
                    await db.delete(member)
                    await db.commit()
                    return True
                return False
        except Exception as e:
            logger.error("[TeamMemberRepository] Remove failed: %s", str(e))
            return False

    @staticmethod
    async def is_member(team_id: str, user_id: str) -> bool:
        if not HAS_SQLALCHEMY:
            return False
        try:
            async with db_manager.session_maker() as db:
                result = await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == uuid.UUID(team_id),
                        TeamMember.user_id == uuid.UUID(user_id),
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error("[TeamMemberRepository] Is member check failed: %s", str(e))
            return False


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

class DataMigrator:
    """Migrate data from JSON files to PostgreSQL"""

    @staticmethod
    async def migrate_users() -> Dict[str, str]:
        """Migrate users from data/users.json"""
        users_file = Path(__file__).resolve().parent / "data" / "users.json"
        if not users_file.exists():
            logger.info("[Migration] No users.json found at %s", users_file)
            return {}

        id_mapping = {}
        try:
            with open(users_file, 'r') as f:
                data = json.load(f)

            for user_data in data.get("users", []):
                old_id = user_data.get("id")
                # Check if user exists
                existing = await UserRepository.get_by_username(user_data["username"])
                if existing:
                    id_mapping[old_id] = str(existing.id)
                else:
                    # Create user
                    user = await UserRepository.create(
                        username=user_data["username"],
                        email=user_data.get("email", f"{user_data['username']}@localhost"),
                        hashed_password=user_data.get("hashed_password", ""),
                        is_admin=user_data.get("is_admin", False),
                        is_active=user_data.get("is_active", True),
                        api_quota=user_data.get("api_quota", {}),
                        created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.now(timezone.utc)
                    )
                    if user:
                        id_mapping[old_id] = str(user.id)

            logger.info(f"[Migration] Migrated {len(id_mapping)} users")
            return id_mapping

        except Exception as e:
            logger.error("[Migration] Failed to migrate users: %s", str(e))
            return {}

    @staticmethod
    async def migrate_conversations(user_id_map: Dict[str, str]) -> int:
        """Migrate conversations from JSON files"""
        conversations_dir = Path("data/conversations")
        if not conversations_dir.exists():
            return 0

        count = 0
        try:
            for conv_file in conversations_dir.glob("*.json"):
                try:
                    with open(conv_file, 'r') as f:
                        data = json.load(f)

                    old_user_id = data.get("user_id")
                    if old_user_id and old_user_id in user_id_map:
                        new_user_id = user_id_map[old_user_id]
                        await ConversationRepository.create(
                            user_id=new_user_id,
                            title=data.get("title"),
                            messages=data.get("messages", []),
                            metadata=data.get("metadata", {})
                        )
                        count += 1
                except Exception as e:
                    logger.warning("[Migration] Failed to migrate conversation {conv_file}: %s", str(e))

            logger.info(f"[Migration] Migrated {count} conversations")
            return count
        except Exception as e:
            logger.error("[Migration] Failed to migrate conversations: %s", str(e))
            return 0

    @staticmethod
    async def run_full_migration() -> Dict[str, Any]:
        """Run all migrations"""
        results = {"users": 0, "conversations": 0, "errors": []}
        try:
            user_mapping = await DataMigrator.migrate_users()
            results["users"] = len(user_mapping)

            if user_mapping:
                conv_count = await DataMigrator.migrate_conversations(user_mapping)
                results["conversations"] = conv_count

        except Exception as e:
            results["errors"].append("An internal error occurred")

        return results


# ============================================================================
# BACKUP/RESTORE
# ============================================================================

class BackupManager:
    """Manage database backups and restores"""

    @staticmethod
    async def create_backup() -> Dict[str, Any]:
        """Create a full database backup as JSON"""
        backup_data = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tables": {}
        }

        try:
            if HAS_SQLALCHEMY:
                async with db_manager.session_maker() as db:
                    # Backup users
                    result = await db.execute(select(User))
                    users = result.scalars().all()
                    backup_data["tables"]["users"] = [u.to_dict() for u in users]

                    # Backup conversations
                    result = await db.execute(select(Conversation))
                    conversations = result.scalars().all()
                    backup_data["tables"]["conversations"] = [c.to_dict() for c in conversations]

                    # Backup voice models
                    result = await db.execute(select(VoiceModel))
                    models = result.scalars().all()
                    backup_data["tables"]["voice_models"] = [m.to_dict() for m in models]

                    # Backup job applications
                    result = await db.execute(select(JobApplication))
                    apps = result.scalars().all()
                    backup_data["tables"]["job_applications"] = [a.to_dict() for a in apps]

                    # Backup documents
                    result = await db.execute(select(Document))
                    docs = result.scalars().all()
                    backup_data["tables"]["documents"] = [d.to_dict() for d in docs]

                    # Backup analytics events (limit to last 1000)
                    result = await db.execute(select(AnalyticsEvent).order_by(AnalyticsEvent.timestamp.desc()).limit(1000))
                    events = result.scalars().all()
                    backup_data["tables"]["analytics_events"] = [e.to_dict() for e in events]

                    # Backup audit logs (limit to last 1000)
                    result = await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1000))
                    logs = result.scalars().all()
                    backup_data["tables"]["audit_logs"] = [l.to_dict() for l in logs]

            logger.info("[Backup] Created full backup")
            return backup_data

        except Exception as e:
            logger.error("[Backup] Failed: %s", str(e))
            raise

    @staticmethod
    async def restore_backup(backup_data: Dict[str, Any]) -> Dict[str, int]:
        """Restore database from backup JSON"""
        restored = {}
        if not HAS_SQLALCHEMY:
            return restored

        try:
            async with db_manager.session_maker() as db:
                # Clear tables in order (respect foreign keys)
                await db.execute(delete(AuditLog))
                await db.execute(delete(AnalyticsEvent))
                await db.execute(delete(Document))
                await db.execute(delete(TeamMember))
                await db.execute(delete(Team))
                await db.execute(delete(IntegrationConfig))
                await db.execute(delete(CRMConfig))
                await db.execute(delete(UserAPIKey))
                await db.execute(delete(InterviewSession))
                await db.execute(delete(JobApplication))
                await db.execute(delete(VoiceModel))
                await db.execute(delete(Conversation))
                await db.execute(delete(User))
                await db.commit()

                # Restore users
                users_data = backup_data.get("tables", {}).get("users", [])
                for u_data in users_data:
                    user = User(
                        id=uuid.UUID(u_data["id"]) if u_data.get("id") else uuid.uuid4(),
                        username=u_data["username"],
                        email=u_data.get("email", ""),
                        hashed_password=u_data.get("hashed_password", ""),
                        is_admin=u_data.get("is_admin", False),
                        is_active=u_data.get("is_active", True),
                    )
                    db.add(user)
                restored["users"] = len(users_data)

                await db.commit()

            logger.info(f"[Restore] Completed: {restored}")
            return restored

        except Exception as e:
            logger.error("[Restore] Failed: %s", str(e))
            raise


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Database manager
    "db_manager", "DatabaseManager",
    "init_database", "close_database",

    # Models
    "User", "Conversation", "VoiceModel", "JobApplication",
    "InterviewSession", "AnalyticsEvent", "UserAPIKey", "Document",
    "CRMConfig", "IntegrationConfig", "Team", "TeamMember", "AuditLog",

    # Repositories
    "UserRepository", "ConversationRepository", "VoiceModelRepository",
    "JobApplicationRepository", "AnalyticsRepository", "DocumentRepository",
    "AuditLogRepository", "UserAPIKeyRepository",
    "IntegrationConfigRepository", "TeamRepository", "TeamMemberRepository",

    # Utilities
    "DataMigrator", "BackupManager",

    # Config
    "HAS_SQLALCHEMY", "DATABASE_URL",
]
