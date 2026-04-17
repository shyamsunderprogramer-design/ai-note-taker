"""
Audit logging module
Logs all security-relevant operations for compliance and debugging
T7: Now writes to database first, JSONL file as fallback
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path

logger = logging.getLogger("audit")

# Audit log storage (JSONL fallback)
AUDIT_LOG_DIR = os.getenv("AUDIT_LOG_DIR", "data/audit_logs")
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "audit.jsonl")


@dataclass
class AuditEvent:
    """Structured audit log entry"""
    timestamp: str
    event_type: str        # "auth_login", "auth_logout", "auth_failure", "data_create", "data_update", "data_delete", "config_change"
    actor: str             # username or IP
    action: str            # What was done
    resource: str           # What was affected
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True


def _ensure_log_dir():
    """Ensure audit log directory exists"""
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


def _write_to_jsonl(event: AuditEvent):
    """Write audit event to JSONL file (fallback)"""
    try:
        _ensure_log_dir()
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log to JSONL: {e}")


async def _write_to_database(event: AuditEvent) -> bool:
    """Write audit event to database via AuditLogRepository. Returns True on success."""
    try:
        from database import AuditLogRepository, HAS_SQLALCHEMY
        if not HAS_SQLALCHEMY:
            return False

        result = await AuditLogRepository.create(
            action=event.event_type,
            resource_type=event.resource,
            resource_id="",
            details={
                "actor": event.actor,
                "action_detail": event.action,
                **event.details,
            },
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            success=event.success,
        )
        return result is not None
    except Exception as e:
        logger.debug(f"Database audit write failed (will use JSONL fallback): {e}")
        return False


def log_audit_event(
    event_type: str,
    actor: str,
    action: str,
    resource: str = "",
    details: Optional[Dict[str, Any]] = None,
    ip_address: str = "",
    user_agent: str = "",
    success: bool = True
):
    """Log an audit event to database (primary) + JSONL (fallback) + Python logger"""
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        event_type=event_type,
        actor=actor,
        action=action,
        resource=resource,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
    )

    # Try database write (async) — if it fails, JSONL is always the safety net
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context — schedule as task
            asyncio.ensure_future(_write_to_database(event))
        else:
            # We're outside async — run synchronously
            loop.run_until_complete(_write_to_database(event))
    except RuntimeError:
        # No event loop — just use JSONL
        pass

    # Always write to JSONL as fallback/secondary store
    _write_to_jsonl(event)

    # Also log to Python logger
    level = logging.INFO if success else logging.WARNING
    logger.log(level, f"[AUDIT] {event_type} actor={actor} action={action} resource={resource} success={success}")


def get_audit_log(limit: int = 100, event_type: Optional[str] = None, actor: Optional[str] = None) -> list:
    """Read audit log entries with optional filtering (from JSONL file)"""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []

    entries = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if event_type and entry.get("event_type") != event_type:
                        continue
                    if actor and entry.get("actor") != actor:
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Failed to read audit log: {e}")

    return entries[-limit:]


async def get_audit_log_from_db(limit: int = 100, action: Optional[str] = None, user_id: Optional[str] = None) -> list:
    """Read audit log entries from database (primary source when available)"""
    try:
        from database import AuditLogRepository, HAS_SQLALCHEMY
        if not HAS_SQLALCHEMY:
            return []
        logs = await AuditLogRepository.get_logs(user_id=user_id, action=action, limit=limit)
        return [log.to_dict() for log in logs]
    except Exception as e:
        logger.error(f"Failed to read audit log from database: {e}")
        return []


def get_audit_stats() -> Dict[str, Any]:
    """Get audit log statistics"""
    entries = get_audit_log(limit=10000)
    if not entries:
        return {"total_events": 0}

    # Count by event type
    type_counts = {}
    for entry in entries:
        et = entry.get("event_type", "unknown")
        type_counts[et] = type_counts.get(et, 0) + 1

    # Count failures
    failures = sum(1 for e in entries if not e.get("success", True))

    return {
        "total_events": len(entries),
        "event_types": type_counts,
        "failures": failures,
        "last_event": entries[-1].get("timestamp") if entries else None,
    }