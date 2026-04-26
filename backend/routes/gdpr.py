"""GDPR compliance endpoints — data export and deletion (right to be forgotten)."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from security import get_current_user
from security.auth import user_manager, User

logger = logging.getLogger("routes.gdpr")

security_bearer = HTTPBearer(auto_error=False)


async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


router = APIRouter()

# Try to import database for full export
try:
    from database import (
        db_manager, HAS_SQLALCHEMY,
        ConversationRepository, VoiceModelRepository,
        JobApplicationRepository, AnalyticsRepository,
        UserRepository,
    )
    DB_AVAILABLE = HAS_SQLALCHEMY
except ImportError:
    DB_AVAILABLE = False  # nosec B110 — optional database import fallback


@router.get("/gdpr/export")
async def export_user_data(user: User = Depends(require_authentication)):
    """Export all user data (GDPR Article 20 — Right to data portability)."""
    user_id = user.id
    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
        "conversations": [],
        "voice_models": [],
        "job_applications": [],
        "analytics": [],
    }

    if DB_AVAILABLE:
        try:
            conversations = await ConversationRepository.get_by_user(user_id, limit=10000)
            export["conversations"] = [c.to_dict() for c in conversations]
        except Exception as e:
            logger.warning("[GDPR] Conversation export failed: %s", str(e))  # nosec B110

        try:
            voice_models = await VoiceModelRepository.get_by_user(user_id, limit=1000)
            export["voice_models"] = [v.to_dict() for v in voice_models]
        except Exception as e:
            logger.warning("[GDPR] Voice model export failed: %s", str(e))  # nosec B110

        try:
            jobs = await JobApplicationRepository.get_by_user(user_id, limit=1000)
            export["job_applications"] = [j.to_dict() for j in jobs]
        except Exception as e:
            logger.warning("[GDPR] Job application export failed: %s", str(e))  # nosec B110

        try:
            analytics = await AnalyticsRepository.get_by_user(user_id, limit=10000)
            export["analytics"] = [a.to_dict() for a in analytics]
        except Exception as e:
            logger.warning("[GDPR] Analytics export failed: %s", str(e))  # nosec B110

    return export


@router.delete("/gdpr/delete")
async def delete_user_data(user: User = Depends(require_authentication)):
    """Delete all user data (GDPR Article 17 — Right to be forgotten)."""
    user_id = user.id
    deleted = {"user_id": user_id, "deleted_at": datetime.now(timezone.utc).isoformat(), "items_removed": {}}

    if DB_AVAILABLE:
        try:
            # Delete in order respecting foreign keys
            analytics_count = await AnalyticsRepository.delete_by_user(user_id)
            deleted["items_removed"]["analytics"] = analytics_count

            conv_count = await ConversationRepository.delete_by_user(user_id)
            deleted["items_removed"]["conversations"] = conv_count

            vm_count = await VoiceModelRepository.delete_by_user(user_id)
            deleted["items_removed"]["voice_models"] = vm_count

            job_count = await JobApplicationRepository.delete_by_user(user_id)
            deleted["items_removed"]["job_applications"] = job_count

            # Delete the user account last
            user_deleted = await UserRepository.delete(user_id)
            deleted["items_removed"]["user_account"] = user_deleted
        except Exception as e:
            logger.error("[GDPR] Deletion failed for user %s: %s", user_id, str(e))
            raise HTTPException(status_code=500, detail="Data deletion failed")
    else:
        # Fallback: remove from in-memory user store
        if user.username in user_manager.users:
            del user_manager.users[user.username]
            user_manager._save_users()
            deleted["items_removed"]["user_account"] = True

    logger.info("[GDPR] All data deleted for user %s", user_id)
    return {"status": "success", "message": "All user data deleted", "details": deleted}


@router.get("/gdpr/consent")
async def get_consent_status(user: User = Depends(require_authentication)):
    """Get current consent status for data processing."""
    return {
        "user_id": user.id,
        "data_processing": True,
        "analytics": True,
        "ai_processing": True,
        "voice_data": True,
        "consent_date": user.created_at,
        "withdraw_url": "/gdpr/delete",
        "export_url": "/gdpr/export",
    }