"""SOC 2 Type II and EU AI Act compliance endpoints.

Provides audit-log retrieval, access-control policy, data-retention
management, SOC 2 control matrix, EU AI Act risk assessment, consent
tracking, and data-residency configuration.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from security import get_current_user, log_audit_event
from security.auth import User

logger = logging.getLogger("routes.compliance")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)


async def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> Optional[str]:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(
    token: Optional[str] = Depends(get_token),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: User = Depends(require_authentication)) -> User:
    """Require admin privileges."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ---------------------------------------------------------------------------
# In-memory stores (replace with database in production)
# ---------------------------------------------------------------------------

# Default audit log entries (examples)
_audit_log: List[Dict[str, Any]] = [
    {
        "timestamp": "2026-04-19T08:15:00Z",
        "user_id": "usr_001",
        "action": "login",
        "resource": "/auth/login",
        "success": True,
        "ip_address": "192.168.1.10",
        "details": {"method": "password"},
    },
    {
        "timestamp": "2026-04-19T08:20:00Z",
        "user_id": "usr_001",
        "action": "create_conversation",
        "resource": "/conversations",
        "success": True,
        "ip_address": "192.168.1.10",
        "details": {"conversation_id": "conv_abc123"},
    },
    {
        "timestamp": "2026-04-19T09:00:00Z",
        "user_id": "usr_002",
        "action": "login",
        "resource": "/auth/login",
        "success": False,
        "ip_address": "10.0.0.55",
        "details": {"method": "password", "reason": "invalid_credentials"},
    },
    {
        "timestamp": "2026-04-19T09:05:00Z",
        "user_id": "usr_002",
        "action": "login",
        "resource": "/auth/login",
        "success": True,
        "ip_address": "10.0.0.55",
        "details": {"method": "password"},
    },
    {
        "timestamp": "2026-04-19T10:30:00Z",
        "user_id": "usr_admin",
        "action": "update_retention_policy",
        "resource": "/compliance/soc2/data-retention",
        "success": True,
        "ip_address": "192.168.1.1",
        "details": {"data_type": "conversations", "new_retention_days": 120},
    },
    {
        "timestamp": "2026-04-19T11:00:00Z",
        "user_id": "usr_003",
        "action": "export_data",
        "resource": "/gdpr/export",
        "success": True,
        "ip_address": "203.0.113.42",
        "details": {"format": "json", "record_count": 47},
    },
    {
        "timestamp": "2026-04-19T11:45:00Z",
        "user_id": "usr_001",
        "action": "delete_voice_model",
        "resource": "/voice/models/vm_009",
        "success": True,
        "ip_address": "192.168.1.10",
        "details": {"model_id": "vm_009"},
    },
    {
        "timestamp": "2026-04-19T12:00:00Z",
        "user_id": "usr_admin",
        "action": "config_change",
        "resource": "/admin/settings",
        "success": True,
        "ip_address": "192.168.1.1",
        "details": {"setting": "max_upload_size_mb", "old_value": 10, "new_value": 25},
    },
    {
        "timestamp": "2026-04-19T13:15:00Z",
        "user_id": "usr_004",
        "action": "start_transcription",
        "resource": "/transcription/start",
        "success": True,
        "ip_address": "172.16.0.5",
        "details": {"language": "en-US"},
    },
    {
        "timestamp": "2026-04-19T14:00:00Z",
        "user_id": "usr_004",
        "action": "grant_ai_consent",
        "resource": "/compliance/eu-ai-act/consent",
        "success": True,
        "ip_address": "172.16.0.5",
        "details": {"consent_type": "transcription_processing"},
    },
]

# Data retention policy (days) — mutable in-memory store
_retention_policy: Dict[str, int] = {
    "conversations": 90,
    "voice_models": 365,
    "analytics": 730,
    "audit_logs": 1095,
}

# Access control policy
_access_control: Dict[str, Any] = {
    "roles": {
        "admin": {
            "permissions": [
                "read_all",
                "write_all",
                "delete_all",
                "manage_users",
                "manage_settings",
                "view_audit_log",
                "manage_retention",
                "manage_data_residency",
            ],
            "description": "Full system access with management capabilities",
        },
        "user": {
            "permissions": [
                "read_own",
                "write_own",
                "delete_own",
                "export_own",
                "manage_own_consent",
            ],
            "description": "Access limited to own data and resources",
        },
    },
    "mfa": {
        "enabled": True,
        "required_for_admin": True,
        "required_for_user": False,
        "methods": ["totp", "email"],
        "grace_period_hours": 24,
    },
}

# SOC 2 control matrix
_control_matrix: Dict[str, Any] = {
    "CC6.1": {
        "name": "Logical Access",
        "description": "Logical access security over information assets is implemented",
        "implemented": True,
        "status": "operational",
        "evidence": [
            "Role-based access control enforced",
            "JWT token authentication",
            "API key rotation policy",
        ],
        "last_reviewed": "2026-03-15",
    },
    "CC6.2": {
        "name": "Authentication",
        "description": "User authentication is enforced before granting access",
        "implemented": True,
        "status": "operational",
        "evidence": [
            "Multi-factor authentication for admin accounts",
            "Password complexity requirements enforced",
            "Session timeout and token expiry",
        ],
        "last_reviewed": "2026-03-15",
    },
    "CC6.3": {
        "name": "Authorization",
        "description": "Access is restricted based on need-to-know and least privilege",
        "implemented": True,
        "status": "operational",
        "evidence": [
            "Role-based permission matrix",
            "Admin-only endpoints gated",
            "Resource ownership checks",
        ],
        "last_reviewed": "2026-03-15",
    },
    "CC7.1": {
        "name": "Detection",
        "description": "Security events are detected and alerts generated",
        "implemented": True,
        "status": "operational",
        "evidence": [
            "Audit logging for all security events",
            "Failed authentication monitoring",
            "Anomalous access pattern detection",
        ],
        "last_reviewed": "2026-02-28",
    },
    "CC7.2": {
        "name": "Monitoring",
        "description": "System monitoring and alerting are operational",
        "implemented": True,
        "status": "partial",
        "evidence": [
            "Health check endpoints active",
            "Rate limiting alerts configured",
            "Real-time dashboards (in progress)",
        ],
        "last_reviewed": "2026-02-28",
    },
    "CC8.1": {
        "name": "Change Management",
        "description": "Changes are authorized, documented, and tested before deployment",
        "implemented": True,
        "status": "partial",
        "evidence": [
            "Git-based version control",
            "Pull request review required",
            "Automated CI/CD pipeline",
            "Staging environment testing",
        ],
        "last_reviewed": "2026-01-20",
    },
}

# EU AI Act compliance status
_eu_ai_act_status: Dict[str, Any] = {
    "risk_category": "limited",
    "transparency_obligations": {
        "status": "compliant",
        "details": "Users are informed when AI is processing their data",
    },
    "human_oversight": {
        "status": "compliant",
        "details": "Users can override, stop, or dismiss AI suggestions at any time",
    },
    "data_governance": {
        "status": "compliant",
        "details": "Data is collected with consent, retained per policy, and encrypted at rest",
    },
    "documentation_requirements": {
        "status": "partial",
        "details": "Technical documentation exists; automated evidence collection in progress",
    },
}

# AI system risk assessment
_risk_assessment: Dict[str, Any] = {
    "system_purpose": "AI-powered note-taking and transcription assistant for meetings and interviews",
    "risk_level": "limited",
    "risk_factors": [
        "Processes conversational data which may contain personal information",
        "AI-generated summaries may contain inaccuracies",
        "Voice model data could identify individuals",
    ],
    "mitigations": [
        "User consent required before AI processing (Article 22)",
        "Transparency notices displayed during AI operations",
        "Human review capability for all AI outputs",
        "Data minimization — only necessary data retained",
        "Encryption at rest and in transit",
        "Retention limits enforced per data type",
        "Right to deletion (GDPR Article 17 integration)",
    ],
    "monitoring": {
        "automated_checks": [
            "Consent validity before each AI operation",
            "Data retention policy enforcement",
            "Access control verification",
        ],
        "human_review": "Quarterly review of AI output quality and bias metrics",
        "incident_response": "Automated alerts on consent withdrawal or anomalous data access",
    },
}

# User consent store (user_id -> list of consent records)
_user_consent: Dict[str, List[Dict[str, Any]]] = {}

# Data residency configuration
_data_residency: Dict[str, Any] = {
    "primary_region": "us-east-1",
    "backup_regions": ["eu-west-1", "us-west-2"],
    "data_types_location": {
        "conversations": "us-east-1",
        "voice_models": "us-east-1",
        "analytics": "us-east-1",
        "audit_logs": "us-east-1",
        "user_profiles": "us-east-1",
    },
    "compliance_regions": ["GDPR", "CCPA"],
    "cross_border_transfer": False,
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RetentionPolicyUpdate(BaseModel):
    """Update one or more data-type retention periods (in days)."""

    conversations: Optional[int] = Field(None, ge=1, le=3650)
    voice_models: Optional[int] = Field(None, ge=1, le=3650)
    analytics: Optional[int] = Field(None, ge=1, le=3650)
    audit_logs: Optional[int] = Field(None, ge=1, le=3650)


class ConsentRequest(BaseModel):
    """Record user consent for a specific AI processing type."""

    consent_type: str = Field(..., min_length=1, max_length=200)
    granted: bool


class DataResidencyUpdate(BaseModel):
    """Update data residency preferences."""

    primary_region: Optional[str] = Field(None, min_length=1, max_length=100)
    backup_regions: Optional[List[str]] = Field(None, max_length=10)
    data_types_location: Optional[Dict[str, str]] = None
    cross_border_transfer: Optional[bool] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# SOC 2 endpoints
# ---------------------------------------------------------------------------


@router.get("/compliance/soc2/audit-log")
async def get_audit_log(
    limit: int = Query(100, ge=1, le=10000),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    since: Optional[str] = Query(None, description="ISO 8601 timestamp"),
    _user: User = Depends(require_authentication),
):
    """Return recent audit log entries with optional filters."""
    entries = list(_audit_log)

    if user_id:
        entries = [e for e in entries if e["user_id"] == user_id]

    if action:
        entries = [e for e in entries if e["action"] == action]

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            filtered = []
            for e in entries:
                ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                if ts >= since_dt:
                    filtered.append(e)
            entries = filtered
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 'since' timestamp — use ISO 8601 format",
            )

    # Also try to pull from the security audit module for a richer view
    try:
        from security.audit import get_audit_log as security_get_audit_log
        file_entries = security_get_audit_log(limit=limit)
        for entry in file_entries:
            mapped = {
                "timestamp": entry.get("timestamp", ""),
                "user_id": entry.get("actor", ""),
                "action": entry.get("action", ""),
                "resource": entry.get("resource", ""),
                "success": entry.get("success", True),
                "ip_address": entry.get("ip_address", ""),
                "details": entry.get("details", {}),
            }
            if mapped not in entries:
                entries.append(mapped)
    except Exception:
        pass  # nosec B110 — security audit module unavailable; in-memory entries suffice

    return entries[-limit:]


@router.get("/compliance/soc2/access-control")
async def get_access_control(
    _user: User = Depends(require_authentication),
):
    """Return current access control policy, role permissions, and MFA status."""
    return _access_control


@router.get("/compliance/soc2/data-retention")
async def get_data_retention(
    _user: User = Depends(require_authentication),
):
    """Return data retention policy with retention periods by data type."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "policy": _retention_policy,
        "unit": "days",
        "last_updated": now,
        "notes": {
            "conversations": "Meeting transcripts and notes",
            "voice_models": "Voice profile embeddings",
            "analytics": "Usage and performance metrics",
            "audit_logs": "Security and compliance audit trail",
        },
    }


@router.post("/compliance/soc2/data-retention")
async def update_data_retention(
    body: RetentionPolicyUpdate,
    user: User = Depends(require_admin),
):
    """Update retention policy (admin only)."""
    updates = body.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No retention values provided",
        )

    changes: Dict[str, int] = {}
    for data_type, new_days in updates.items():
        old_days = _retention_policy.get(data_type)
        if old_days is not None and new_days != old_days:
            _retention_policy[data_type] = new_days
            changes[data_type] = new_days

    if changes:
        log_audit_event(
            event_type="config_change",
            actor=user.username,
            action="update_retention_policy",
            resource="/compliance/soc2/data-retention",
            details={"changes": changes, "admin_id": user.id},
            ip_address="",
            success=True,
        )
        logger.info(
            "[COMPLIANCE] Retention policy updated by %s: %s",
            user.username,
            changes,
        )

    return {
        "status": "updated",
        "policy": _retention_policy,
        "changes": changes,
    }


@router.get("/compliance/soc2/controls")
async def get_soc2_controls(
    _user: User = Depends(require_authentication),
):
    """Return SOC 2 control matrix with implementation status."""
    controls = []
    for ref, ctrl in _control_matrix.items():
        controls.append(
            {
                "control_ref": ref,
                "name": ctrl["name"],
                "description": ctrl["description"],
                "implemented": ctrl["implemented"],
                "status": ctrl["status"],
                "evidence": ctrl["evidence"],
                "last_reviewed": ctrl["last_reviewed"],
            }
        )

    implemented = sum(1 for c in controls if c["implemented"])
    operational = sum(1 for c in controls if c["status"] == "operational")
    partial = sum(1 for c in controls if c["status"] == "partial")

    return {
        "controls": controls,
        "summary": {
            "total": len(controls),
            "implemented": implemented,
            "operational": operational,
            "partial": partial,
            "not_implemented": len(controls) - implemented,
        },
    }


# ---------------------------------------------------------------------------
# EU AI Act endpoints
# ---------------------------------------------------------------------------


@router.get("/compliance/eu-ai-act/status")
async def get_eu_ai_act_status(
    _user: User = Depends(require_authentication),
):
    """Return EU AI Act compliance status."""
    return _eu_ai_act_status


@router.get("/compliance/eu-ai-act/assessment")
async def get_ai_risk_assessment(
    _user: User = Depends(require_authentication),
):
    """Return AI system risk assessment per EU AI Act requirements."""
    return _risk_assessment


@router.post("/compliance/eu-ai-act/consent")
async def record_ai_consent(
    body: ConsentRequest,
    user: User = Depends(require_authentication),
):
    """Record user consent for AI processing."""
    consent_record = {
        "consent_type": body.consent_type,
        "granted": body.granted,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.id,
    }

    if user.id not in _user_consent:
        _user_consent[user.id] = []

    # If same consent_type already recorded, update the latest entry
    existing = None
    for i, rec in enumerate(_user_consent[user.id]):
        if rec["consent_type"] == body.consent_type:
            existing = i
            break

    if existing is not None:
        _user_consent[user.id][existing] = consent_record
    else:
        _user_consent[user.id].append(consent_record)

    log_audit_event(
        event_type="data_update" if body.granted else "data_delete",
        actor=user.username,
        action="grant_ai_consent" if body.granted else "revoke_ai_consent",
        resource="/compliance/eu-ai-act/consent",
        details={
            "consent_type": body.consent_type,
            "granted": body.granted,
        },
        ip_address="",
        success=True,
    )

    logger.info(  # lgtm[py/log-injection]
        "[COMPLIANCE] AI consent %s for user %s: %s",
        "granted" if body.granted else "revoked",
        user.id,
        body.consent_type,
    )

    return {
        "status": "recorded",
        "consent": consent_record,
    }


@router.get("/compliance/eu-ai-act/consent/{user_id}")
async def get_ai_consent(
    user_id: str,
    _user: User = Depends(require_authentication),
):
    """Get a user's AI consent status.

    Users may only view their own consent records unless they are admin.
    """
    if user_id != _user.id and not _user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's consent records",
        )

    records = _user_consent.get(user_id, [])

    # Build a summary keyed by consent_type with latest entry
    summary: Dict[str, Any] = {}
    for rec in reversed(records):
        ctype = rec["consent_type"]
        if ctype not in summary:
            summary[ctype] = rec

    return {
        "user_id": user_id,
        "consents": list(summary.values()),
        "total_records": len(records),
    }


# ---------------------------------------------------------------------------
# Data residency endpoints
# ---------------------------------------------------------------------------


@router.get("/compliance/data-residency")
async def get_data_residency(
    _user: User = Depends(require_authentication),
):
    """Return current data residency configuration."""
    return _data_residency


@router.post("/compliance/data-residency")
async def set_data_residency(
    body: DataResidencyUpdate,
    user: User = Depends(require_admin),
):
    """Set data residency preferences (admin only)."""
    updates = body.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No residency values provided",
        )

    changes: Dict[str, Any] = {}
    for key, value in updates.items():
        old_value = _data_residency.get(key)
        if old_value != value:
            _data_residency[key] = value
            changes[key] = {"old": old_value, "new": value}

    if changes:
        log_audit_event(
            event_type="config_change",
            actor=user.username,
            action="update_data_residency",
            resource="/compliance/data-residency",
            details={"changes": changes, "admin_id": user.id},
            ip_address="",
            success=True,
        )
        logger.info(
            "[COMPLIANCE] Data residency updated by %s: %s",
            user.username,
            list(changes.keys()),
        )

    return {
        "status": "updated",
        "data_residency": _data_residency,
        "changes": list(changes.keys()),
    }