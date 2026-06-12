"""Route module for authentication and audit log endpoints."""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Query

from security import (
    create_access_token, create_refresh_token, verify_refresh_token,
    get_current_user, rate_limit,
    log_audit_event, get_audit_log, get_audit_stats,
    InputValidator, ErrorCode, error_response,
)
from security.auth import user_manager, User

logger = logging.getLogger("routes.auth")

# Auth helpers — these live in main.py but are needed here.
# They will be imported from a shared deps module in a future refactor.
from fastapi import status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends as _Depends

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = _Depends(security_bearer)) -> str:
    """Extract token from Authorization header"""
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = _Depends(get_token_from_request)):
    """Require authentication for protected endpoints"""
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
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: User = _Depends(require_authentication)):
    """Require admin privileges"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


router = APIRouter()


@router.post("/auth/register")
@rate_limit(requests_per_minute=5, window_seconds=60)
async def register_user(
    username: str = Form(..., min_length=3, max_length=30),
    email: str = Form(...),
    password: str = Form(..., min_length=8)  # nosec B105 — form parameter
):
    """Register a new user account"""
    # Validate inputs
    if not InputValidator.validate_username(username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username. Use 3-30 alphanumeric characters, underscores, or hyphens."
        )

    if not InputValidator.validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        user = user_manager.create_user(username=username, email=email, password=password)
        log_audit_event("auth_register", username, "user_registered", resource=f"user:{user.id}", success=True)
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": user.id,
            "username": user.username
        }
    except ValueError as e:
        log_audit_event("auth_register", username, "user_register_failed", details={"reason": str(e)}, success=False)
        raise HTTPException(status_code=400, detail="Registration failed")


@router.post("/auth/login")
@rate_limit(requests_per_minute=10, window_seconds=60)
async def login_user(username: str = Form(...), password: str = Form(...)):  # nosec B105
    """Login and get JWT token"""
    user = user_manager.authenticate_user(username, password)
    if not user:
        log_audit_event("auth_failure", username, "login_failed", resource="auth", success=False)
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    log_audit_event("auth_login", username, "user_logged_in", resource=f"user:{user.id}", success=True)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(hours=24)
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24 hours in seconds
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }


@router.get("/auth/me")
async def get_current_user_info(user: User = Depends(require_authentication)):
    """Get current authenticated user info"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "last_login": user.last_login,
        "api_quota": user.api_quota
    }


@router.post("/auth/logout")
async def logout_user(user: User = Depends(require_authentication)):
    """Logout (client should delete token)"""
    log_audit_event("auth_logout", user.username, "user_logged_out", resource=f"user:{user.id}", success=True)
    # Note: JWT tokens are stateless, actual logout is client-side
    return {"status": "success", "message": "Logged out successfully"}


@router.post("/auth/reset-password")
async def reset_password(
    username: str = Form(...),
    new_password: str = Form(..., min_length=8)  # nosec B105
):
    """Reset password for a user account (for local/self-hosted use)"""
    user = user_manager.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_manager.update_password(username, new_password)
    log_audit_event("auth_reset_password", username, "password_reset", resource=f"user:{user.id}", success=True)
    return {"status": "success", "message": "Password reset successfully"}


@router.post("/auth/refresh")
@rate_limit(requests_per_minute=10, window_seconds=60)
async def refresh_access_token(refresh_token: str = Form(...)):
    """Refresh an access token using a refresh token"""
    token_data = verify_refresh_token(refresh_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = user_manager.users.get(token_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(hours=24)
    )

    log_audit_event("auth_refresh", user.username, "token_refreshed", resource=f"user:{user.id}", success=True)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400
    }


@router.get("/audit/log")
async def get_audit_log_endpoint(
    user: User = Depends(require_authentication),
    limit: int = Query(100, ge=1, le=1000),
    event_type: str = Query(None, description="Filter by event type"),
    actor: str = Query(None, description="Filter by actor"),
):
    """Get audit log entries (requires authentication)."""
    if not user.is_admin:
        return error_response(ErrorCode.FORBIDDEN, "Admin access required", status_code=403)
    entries = get_audit_log(limit=limit, event_type=event_type, actor=actor)
    return {"entries": entries, "count": len(entries)}


@router.get("/audit/stats")
async def get_audit_stats_endpoint(
    user: User = Depends(require_authentication),
):
    """Get audit log statistics (requires authentication)."""
    if not user.is_admin:
        return error_response(ErrorCode.FORBIDDEN, "Admin access required", status_code=403)
    return get_audit_stats()