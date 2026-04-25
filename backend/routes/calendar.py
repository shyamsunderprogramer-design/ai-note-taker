"""Calendar integration — Google Calendar OAuth + auto-join detection."""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from routes.deps import require_authentication
from routes.integration_helpers import get_integration_config, save_integration_config, delete_integration_config
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.calendar")

router = APIRouter()

# Ephemeral upcoming meetings (production: Calendar API)
_upcoming_meetings: List[Dict] = []


@router.get("/calendar/status")
async def get_calendar_status(user: User = Depends(require_authentication)):
    """Check if calendar integration is configured."""
    cfg = await get_integration_config(user.id, "calendar")
    if not cfg["connected"]:
        return {
            "connected": False,
            "provider": None,
            "auto_join": False,
            "last_sync": None,
        }
    config = cfg.get("config", {})
    return {
        "connected": True,
        "provider": config.get("provider"),
        "auto_join": config.get("auto_join", False),
        "last_sync": cfg.get("last_sync_at"),
    }


@router.post("/calendar/configure")
async def configure_calendar(
    provider: str = Query(..., description="google or outlook"),
    auto_join: bool = Query(False, description="Auto-join detected meetings"),
    user: User = Depends(require_authentication),
):
    """Configure calendar integration."""
    if provider not in ("google", "outlook"):
        raise HTTPException(status_code=400, detail="Provider must be 'google' or 'outlook'")

    await save_integration_config(
        user.id, "calendar",
        config={"provider": provider, "auto_join": auto_join},
        enabled=True,
    )

    log_audit_event("calendar_configure", user.username, "calendar_configured",
                     resource=f"calendar:{provider}", success=True)

    # Return OAuth URL for the provider
    if provider == "google":
        client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "")
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&redirect_uri=http://localhost:8000/calendar/callback&"
            f"scope=https://www.googleapis.com/auth/calendar.readonly&"
            f"response_type=code&access_type=offline"
        ) if client_id else ""
        return {
            "status": "configured",
            "provider": provider,
            "auth_url": auth_url,
            "message": "Visit the auth_url to grant calendar access" if auth_url else "Set GOOGLE_CALENDAR_CLIENT_ID to enable OAuth",
        }
    else:
        return {
            "status": "configured",
            "provider": provider,
            "message": "Outlook calendar configured. Set OUTLOOK_CLIENT_ID to enable OAuth.",
        }


@router.get("/calendar/upcoming")
async def get_upcoming_meetings(
    hours: int = Query(24, description="Hours ahead to check"),
    user: User = Depends(require_authentication),
):
    """Get upcoming meetings from connected calendar."""
    cfg = await get_integration_config(user.id, "calendar")
    if not cfg["connected"]:
        return {"meetings": [], "message": "Calendar not connected. Use /calendar/configure first."}

    config = cfg.get("config", {})
    return {
        "meetings": _upcoming_meetings,
        "hours_ahead": hours,
        "provider": config.get("provider"),
        "auto_join": config.get("auto_join", False),
    }


@router.post("/calendar/auto-join")
async def set_auto_join(
    enabled: bool = Query(...),
    user: User = Depends(require_authentication),
):
    """Toggle auto-join for detected meetings."""
    cfg = await get_integration_config(user.id, "calendar")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Calendar not connected")

    config = cfg.get("config", {})
    config["auto_join"] = enabled
    await save_integration_config(
        user.id, "calendar",
        config=config,
        enabled=True,
    )

    return {
        "auto_join": enabled,
        "message": f"Auto-join {'enabled' if enabled else 'disabled'}",
    }


@router.delete("/calendar/disconnect")
async def disconnect_calendar(user: User = Depends(require_authentication)):
    """Disconnect calendar integration."""
    await delete_integration_config(user.id, "calendar")
    log_audit_event("calendar_disconnect", user.username, "calendar_disconnected", success=True)
    return {"status": "disconnected"}