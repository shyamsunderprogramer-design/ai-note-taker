"""Route module for CRM integration endpoints."""
import logging

from fastapi import APIRouter, Body, Depends

from security import ErrorCode, error_response
from security.auth import User

# Auth helpers (mirrored — will be consolidated)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security import get_current_user

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


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
    except Exception as e:
        logger.error("[CRM] Test error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)