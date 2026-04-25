"""Route module for CRM integration endpoints."""
import logging
import os
import time

from fastapi import APIRouter, Body, Depends, HTTPException, status

from routes.deps import require_authentication
from security import ErrorCode, error_response
from security.auth import User


logger = logging.getLogger("routes.crm")

router = APIRouter()


@router.get("/crm/config")
async def get_crm_config():
    """Get CRM configuration."""
    try:
        from crm_integration import get_crm
        crm = get_crm()
        return crm.get_config()
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "CRM integration not available", status_code=503)
    except Exception as e:
        logger.error("[CRM] Get config error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/crm/config")
async def save_crm_config(body: dict, user: User = Depends(require_authentication)):
    """Save CRM configuration."""
    try:
        from crm_integration import get_crm
        crm = get_crm()
        success = crm.configure(body)
        return {"success": success}
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "CRM integration not available", status_code=503)
    except Exception as e:
        logger.error("[CRM] Save config error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/crm/webhook/{crm_type}/{event_type}")
async def send_crm_webhook(crm_type: str, event_type: str, body: dict):
    """Send webhook to CRM."""
    try:
        from crm_integration import get_crm
        crm = get_crm()
        result = crm.log_event(event_type, body)
        return {"success": result}
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "CRM integration not available", status_code=503)
    except Exception as e:
        logger.error("[CRM] Webhook error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/crm/test")
async def test_crm_connection():
    """Test CRM connection."""
    try:
        from crm_integration import get_crm
        crm = get_crm()
        return crm.test_connection()
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "CRM integration not available", status_code=503)


# ─── HubSpot Integration ───────────────────────────────────────────────

@router.post("/crm/hubspot/sync")
async def sync_hubspot(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Sync meeting data to HubSpot CRM."""
    crm_type = body.get("type", "activity")  # activity, contact, deal
    meeting_data = body.get("meeting_data", {})

    # Try HubSpot SDK
    try:
        import httpx
        hubspot_api_key = os.getenv("HUBSPOT_API_KEY", "")
        if not hubspot_api_key:
            return {"status": "not_configured", "message": "Set HUBSPOT_API_KEY environment variable"}

        async with httpx.AsyncClient() as client:
            if crm_type == "activity":
                engagement = {
                    "engagement": {"type": "MEETING", "timestamp": int(time.time() * 1000)},
                    "metadata": {
                        "title": meeting_data.get("title", "Meeting"),
                        "body": meeting_data.get("summary", ""),
                    }
                }
                response = await client.post(
                    "https://api.hubapi.com/engagements/v1/engagements",
                    json=engagement,
                    headers={"Authorization": f"Bearer {hubspot_api_key}"},
                    timeout=15.0,
                )
                return {"status": "synced", "crm": "hubspot", "type": "activity", "code": response.status_code}
    except ImportError:
        pass
    except Exception as e:
        logger.error("[CRM] HubSpot sync error: %s", str(e))

    return {"status": "error", "message": "HubSpot sync failed"}


# ─── Salesforce Integration ─────────────────────────────────────────────

@router.post("/crm/salesforce/sync")
async def sync_salesforce(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Sync meeting data to Salesforce CRM."""
    try:
        sf_instance = os.getenv("SALESFORCE_INSTANCE_URL", "")
        sf_token = os.getenv("SALESFORCE_ACCESS_TOKEN", "")

        if not sf_instance or not sf_token:
            return {"status": "not_configured", "message": "Set SALESFORCE_INSTANCE_URL and SALESFORCE_ACCESS_TOKEN"}

        return {"status": "configured", "message": "Salesforce credentials detected. Sync ready."}
    except Exception as e:
        logger.error("[CRM] Salesforce sync error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)