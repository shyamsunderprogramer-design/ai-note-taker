"""Route module for phone call support and transcription endpoints."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from routes.deps import require_authentication
from routes.integration_helpers import get_integration_config, save_integration_config, delete_integration_config
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.phone")

router = APIRouter()

# Ephemeral call sessions (production: persistent storage)
_call_sessions: Dict[str, dict] = {}
_user_calls: Dict[str, list] = {}

ALLOWED_PROVIDERS = {"twilio", "vonage"}


class ConnectPhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, description="Phone number to connect (E.164 format recommended)")
    provider: str = Field(..., description="Phone provider: 'twilio' or 'vonage'")


class InitiateCallRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, description="Phone number to call (E.164 format recommended)")
    duration_seconds: int = Field(300, ge=10, le=14400, description="Expected call duration in seconds (10s - 4h)")


def _generate_mock_transcription(call_id: str, phone_number: str) -> dict:
    """Generate a placeholder transcription for MVP."""
    return {
        "call_id": call_id,
        "phone_number": phone_number,
        "transcription": (
            "[MVP Placeholder] This is a simulated transcription. "
            "In production, audio from the call would be streamed to a speech-to-text "
            "service (e.g., Deepgram, Whisper) and transcribed in real time."
        ),
        "confidence": 0.0,
        "language": "en-US",
        "segments": [
            {"speaker": "caller", "start": 0.0, "end": 5.0, "text": "[Placeholder] Caller introduction segment."},
            {"speaker": "recipient", "start": 5.5, "end": 12.0, "text": "[Placeholder] Recipient response segment."},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/phone/connect")
async def connect_phone(
    body: ConnectPhoneRequest,
    user: User = Depends(require_authentication),
):
    """Connect a phone number for call transcription."""
    if body.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"provider must be one of: {', '.join(sorted(ALLOWED_PROVIDERS))}")

    now = datetime.now(timezone.utc).isoformat()

    await save_integration_config(
        user.id, "phone",
        config={"provider": body.provider, "phone_number": body.phone_number},
        enabled=True,
    )

    log_audit_event("phone_connect", user.username, "phone_connected", success=True)

    return {
        "status": "connected",
        "phone_number": body.phone_number,
        "provider": body.provider,
        "connected_at": now,
    }


@router.get("/phone/status")
async def get_phone_status(
    user: User = Depends(require_authentication),
):
    """Check phone integration status for the current user."""
    cfg = await get_integration_config(user.id, "phone")
    if not cfg["connected"]:
        return {
            "connected": False,
            "is_active": False,
            "provider": None,
            "phone_number": None,
            "total_calls": 0,
        }

    config = cfg.get("config", {})
    total_calls = len(_user_calls.get(user.id, []))

    return {
        "connected": True,
        "is_active": True,
        "provider": config.get("provider"),
        "phone_number": config.get("phone_number"),
        "total_calls": total_calls,
    }


@router.post("/phone/call")
async def initiate_call(
    body: InitiateCallRequest,
    user: User = Depends(require_authentication),
):
    """Initiate a phone call transcription session."""
    cfg = await get_integration_config(user.id, "phone")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Phone not connected. Call /phone/connect first.")

    config = cfg.get("config", {})
    call_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    call_session = {
        "call_id": call_id,
        "user_id": user.id,
        "phone_number": body.phone_number,
        "duration_seconds": body.duration_seconds,
        "provider": config.get("provider"),
        "status": "initiated",
        "transcription": None,
        "created_at": now,
        "ended_at": None,
        "events": [],
    }

    _call_sessions[call_id] = call_session
    _user_calls.setdefault(user.id, []).append(call_id)

    _masked_phone = body.phone_number[:4] + "****" + body.phone_number[-4:] if len(body.phone_number) > 8 else "****"
    logger.info("[Phone] Call %s initiated by user %s to %s", call_id, user.id, _masked_phone)  # lgtm[py/clear-text-logging-sensitive-data]

    return {
        "call_id": call_id,
        "phone_number": body.phone_number,
        "duration_seconds": body.duration_seconds,
        "status": "initiated",
        "provider": config.get("provider"),
        "created_at": now,
    }


@router.get("/phone/transcription/{call_id}")
async def get_call_transcription(
    call_id: str,
    user: User = Depends(require_authentication),
):
    """Get transcription for a phone call."""
    call_session = _call_sessions.get(call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call not found")
    if call_session["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this call")

    if call_session["transcription"] is None:
        call_session["transcription"] = _generate_mock_transcription(
            call_id, call_session["phone_number"]
        )
        call_session["status"] = "transcribed"

    return {
        "call_id": call_id,
        "status": call_session["status"],
        "phone_number": call_session["phone_number"],
        "transcription": call_session["transcription"],
        "created_at": call_session["created_at"],
        "ended_at": call_session["ended_at"],
    }


@router.post("/phone/webhook")
async def phone_webhook(request: Request):
    """Webhook endpoint for phone provider callbacks. No auth required."""
    content_type = request.headers.get("content-type", "")

    try:
        if "form" in content_type:
            form_data = await request.form()
            data = dict(form_data)
        else:
            data = await request.json()
    except Exception:
        logger.warning("[Phone] Webhook received unparseable payload")
        return {"status": "received", "error": "unparseable payload"}

    call_sid = data.get("CallSid") or data.get("call_id") or data.get("uuid", "")
    call_status = data.get("CallStatus") or data.get("status") or data.get("event", "")

    logger.info("[Phone] Webhook event: call_sid=%s, status=%s", call_sid, call_status)  # lgtm[py/log-injection]

    if call_sid and call_sid in _call_sessions:
        call_session = _call_sessions[call_sid]
        event = {
            "event": call_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_data": {k: str(v) for k, v in data.items()},
        }
        call_session["events"].append(event)

        status_map = {
            "ringing": "ringing", "in-progress": "in_progress", "completed": "completed",
            "busy": "failed", "no-answer": "failed", "failed": "failed", "canceled": "canceled",
        }
        mapped = status_map.get(call_status.lower())
        if mapped:
            call_session["status"] = mapped
        if mapped in ("completed", "failed", "canceled"):
            call_session["ended_at"] = datetime.now(timezone.utc).isoformat()

    if "twilio" in (data.get("AccountSid", "") or "").lower() or "application/xml" in content_type:
        from fastapi.responses import Response
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    return {"status": "received", "call_sid": call_sid, "event": call_status}


@router.delete("/phone/disconnect")
async def disconnect_phone(
    user: User = Depends(require_authentication),
):
    """Disconnect phone integration for the current user."""
    cfg = await get_integration_config(user.id, "phone")
    if not cfg["connected"]:
        raise HTTPException(status_code=404, detail="No phone integration found")

    config = cfg.get("config", {})
    now = datetime.now(timezone.utc).isoformat()

    await delete_integration_config(user.id, "phone")

    log_audit_event("phone_disconnect", user.username, "phone_disconnected", success=True)

    return {
        "status": "disconnected",
        "phone_number": config.get("phone_number"),
        "provider": config.get("provider"),
        "disconnected_at": now,
    }