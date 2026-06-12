"""Route module for authentication and audit log endpoints."""
import asyncio
import json
import logging
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from security import (
    create_access_token, create_refresh_token, verify_refresh_token,
    get_current_user, get_current_user_with_reason, rate_limit,
    log_audit_event, get_audit_log, get_audit_stats,
    session_bus,
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


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Falls back to 'unknown' for the
    in-process TestClient where request.client may be None."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


async def get_token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials = _Depends(security_bearer),
) -> str:
    """Extract token from either the Authorization header (preferred)
    or the ``?token=...`` query param (for SSE EventSource, which
    can't set headers)."""
    if credentials:
        return credentials.credentials
    return request.query_params.get("token")


async def require_authentication(token: str = _Depends(get_token_from_request)):
    """Require authentication for protected endpoints. Single-session
    enforcement (Fix #34): if the token's jti no longer matches the
    user's active_session_id, return 401 with
    ``error_code="session_invalidated"`` so the client can show the
    "you've been logged out" modal instead of the generic "please log
    in again" prompt.
    """
    user, reason = get_current_user_with_reason(token)
    if not user:
        # Map the reason to a 401 body. The error_code field is the
        # contract: clients branch on it to decide whether to show the
        # kicked modal or a generic re-login prompt.
        if reason == "session_invalidated":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated: another device has logged in as this user",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Error-Code": "session_invalidated",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required" if reason in ("no_token",) else "Invalid authentication credentials",
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
        user = await user_manager.create_user(username=username, email=email, password=password)
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
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),  # nosec B105
):
    """Login and get a JWT access + refresh pair.

    Single-session enforcement (Fix #34): the jti on both tokens is
    the user's freshly-rotated ``active_session_id``. Any device
    holding a previously-issued token for this user receives a
    ``session_kicked`` event over SSE and its next API call returns
    401 with ``X-Error-Code: session_invalidated``.
    """
    ip = _client_ip(request)
    ua = _user_agent(request)
    user = await user_manager.authenticate_user(username, password, ip=ip, user_agent=ua)
    if not user:
        log_audit_event("auth_failure", username, "login_failed", resource="auth", success=False)
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # authenticate_user just rotated user.active_session_id; reuse it
    # so the access + refresh share one session.
    jti = user.active_session_id
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(hours=24),
        jti=jti,
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "username": user.username},
        jti=jti,
    )

    log_audit_event("auth_login", username, "user_logged_in", resource=f"user:{user.id}", success=True)

    # Notify any open SSE stream on the old session that the user has
    # been kicked. publish() is a no-op if nothing is subscribed.
    session_bus.publish(user.id, {
        "type": "session_kicked",
        "reason": "new_login",
        "new_session_started_at": user.active_session_started_at,
    })

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token,
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
    """Logout. Clears the server-side active_session_id so the token is
    rejected at verify_token even if a client holds onto it (defence in
    depth on top of client-side deletion). Without this, a stolen
    access token would remain valid until the 8h ACCESS_TOKEN_EXPIRE.

    Fix #35: the JSON ``_save_users`` is gone. We delegate to
    ``UserRepository.clear_session`` which zeros the 4 active_session_*
    columns in a single UPDATE.
    """
    await user_manager.clear_session(user.id)
    log_audit_event("auth_logout", user.username, "user_logged_out", resource=f"user:{user.id}", success=True)
    return {"status": "success", "message": "Logged out successfully"}


@router.post("/auth/reset-password")
async def reset_password(
    username: str = Form(...),
    new_password: str = Form(..., min_length=8)  # nosec B105
):
    """Reset password for a user account (for local/self-hosted use)"""
    user = await user_manager.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user_manager.update_password(username, new_password)
    log_audit_event("auth_reset_password", username, "password_reset", resource=f"user:{user.id}", success=True)
    return {"status": "success", "message": "Password reset successfully"}


@router.post("/auth/refresh")
@rate_limit(requests_per_minute=10, window_seconds=60)
async def refresh_access_token(refresh_token: str = Form(...)):
    """Refresh an access token using a refresh token.

    Single-session enforcement (Fix #34): if the refresh token's
    jti no longer matches the user's active_session_id (because a
    2nd device has logged in since this refresh token was issued),
    reject the refresh with 401 + ``X-Error-Code: session_invalidated``.
    Otherwise re-use the refresh jti so the new access token remains
    valid until the next login-elsewhere.
    """
    token_data = verify_refresh_token(refresh_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await user_manager.get_user(token_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if token_data.jti and user.active_session_id and token_data.jti != user.active_session_id:
        log_audit_event(
            "auth_session_invalidated", user.username,
            "refresh_rejected_session_rotated",
            resource=f"user:{user.id}",
            details={"token_jti": token_data.jti, "active_jti": user.active_session_id},
            success=False,
        )
        raise HTTPException(
            status_code=401,
            detail="Session invalidated: another device has logged in as this user",
            headers={"X-Error-Code": "session_invalidated"},
        )

    jti = token_data.jti or user.active_session_id
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(hours=24),
        jti=jti,
    )

    log_audit_event("auth_refresh", user.username, "token_refreshed", resource=f"user:{user.id}", success=True)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400
    }


@router.get("/auth/events")
async def auth_events(
    request: Request,
    user: User = _Depends(require_authentication),
):
    """SSE stream of session lifecycle events for the current user.

    Browsers connect with ``new EventSource('/auth/events?token=...')``
    (EventSource cannot set the Authorization header — the new
    ``get_token_from_request`` accepts the query-string form for this
    reason). On a 2nd-device login, this stream receives a
    ``session_kicked`` event and the client should drop its tokens
    and show the kicked modal.

    In-process only: the underlying SessionBus is an in-memory dict
    (see ``security/session_bus.py``). With ``uvicorn --workers > 1``
    the login that kicks the session may land on a different worker
    from the one serving this stream; a future PR swaps the in-memory
    dict for Redis pub/sub to make the bus cross-process.
    """
    q = session_bus.subscribe(user.id)

    async def event_stream():
        try:
            # Initial comment flushes the connection open and fires the
            # browser's EventSource ``onopen`` before the first event
            # lands — gives the client a positive signal it's connected.
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Heartbeat — keeps proxies from idling the
                    # connection out, and lets the client notice a
                    # dead link via EventSource's reconnect.
                    yield ": ping\n\n"
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
        finally:
            session_bus.unsubscribe(user.id, q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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