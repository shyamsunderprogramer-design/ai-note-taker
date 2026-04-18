"""Route module for admin operations: backup, restore, migration."""
import logging
from typing import Dict

from fastapi import APIRouter, Body, Depends

from security import ErrorCode, error_response, log_audit_event
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


async def require_admin(user: User = Depends(require_authentication)):
    """Require admin privileges"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


logger = logging.getLogger("routes.admin")

# Database availability
try:
    from database import (
        db_manager, init_database, close_database,
        UserRepository, ConversationRepository, VoiceModelRepository,
        JobApplicationRepository, AnalyticsRepository,
        BackupManager, DataMigrator,
        HAS_SQLALCHEMY,
    )
    DATABASE_AVAILABLE = HAS_SQLALCHEMY
except ImportError as e:
    DATABASE_AVAILABLE = False

router = APIRouter()


@router.post("/admin/backup")
async def admin_create_backup(user: User = Depends(require_admin)):
    """Create a full database backup as JSON - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        backup_data = await BackupManager.create_backup()
        log_audit_event("admin_backup", user.username, "backup_created", success=True)
        return {
            "status": "success",
            "message": "Backup created successfully",
            "backup": backup_data
        }
    except Exception as e:
        log_audit_event("admin_backup", user.username, "backup_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, "Backup failed")


@router.post("/admin/restore")
async def admin_restore_backup(backup_data: Dict = Body(...), user: User = Depends(require_admin)):
    """Restore database from JSON backup - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        restored = await BackupManager.restore_backup(backup_data)
        log_audit_event("admin_restore", user.username, "backup_restored", resource=f"restored:{restored}", success=True)
        return {
            "status": "success",
            "message": "Backup restored successfully",
            "restored": restored
        }
    except Exception as e:
        log_audit_event("admin_restore", user.username, "restore_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, "Restore failed")


@router.post("/admin/migrate")
async def admin_run_migration(user: User = Depends(require_admin)):
    """Run JSON -> PostgreSQL migration - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        results = await DataMigrator.run_full_migration()
        log_audit_event("admin_migrate", user.username, "migration_run", resource=f"users:{results.get('users', 0)}", success=True)
        return {
            "status": "success",
            "message": "Migration completed",
            "results": results
        }
    except Exception as e:
        log_audit_event("admin_migrate", user.username, "migration_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, "Migration failed")