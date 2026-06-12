"""Route module for Single Sign-On via Google and Microsoft OAuth2."""
import os
import logging
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from routes.auth import _client_ip, _user_agent
from routes.deps import require_authentication
from security import create_access_token, log_audit_event, session_bus
from security.auth import user_manager, User
from core.database import UserRepository

logger = logging.getLogger("routes.sso")

router = APIRouter()

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")

# OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

# In-memory state store (single-process; use Redis/db for multi-process)
_pending_states: dict[str, str] = {}  # state -> provider ("google" | "microsoft")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_redirect_uri(provider: str) -> str:
    """Build the callback redirect URI for *provider*.

    In production set SSO_BASE_URL to your public origin (e.g.
    https://app.example.com).  Falls back to localhost:8000.
    """
    import os
    base = os.getenv("SSO_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/sso/{provider}/callback"


async def _auto_create_or_get_user(email: str, name: str, provider: str) -> User:
    """Return existing user by email, or auto-create one.

    Auto-created users get their email as username and a random password
    (since they authenticate via SSO, the password is irrelevant).

    Fix #35: this is now an async function. The pre-Fix-35 version
    iterated ``user_manager.users.values()`` (an in-memory dict).
    The async version uses ``UserRepository.get_by_email`` (an
    indexed DB hit) and bumps ``last_login`` via the dedicated
    ``UserRepository.bump_last_login`` method. The uniqueness loop
    for username derivation is best-effort: the ``users.username``
    unique constraint is the safety net for concurrent inserts.
    """
    orm = await UserRepository.get_by_email(email)
    if orm is not None:
        await UserRepository.bump_last_login(str(orm.id))
        return User.from_orm(orm)

    # Derive a username from the email prefix, ensuring uniqueness.
    base_username = email.split("@")[0]
    username = base_username
    suffix = 1
    while await user_manager.get_user(username) is not None:
        username = f"{base_username}{suffix}"
        suffix += 1

    random_password = secrets.token_urlsafe(32)
    user = await user_manager.create_user(
        username=username,
        email=email,
        password=random_password,
    )
    logger.info("Auto-created user %s via %s SSO", username, provider)
    return user


async def _rotate_session_for(user: User, ip: str = "", user_agent: str = "") -> str:
    """Rotate the user's active session and return the new jti.

    Mirrors ``UserManager.authenticate_user`` for the password login
    path, but is callable from SSO callbacks that don't have a
    password to verify. Single-session enforcement (Fix #34): any
    previously-issued token for this user becomes invalid as soon as
    the new jti is persisted.

    Fix #35: this is now async. The pre-Fix-35 version mutated the
    in-memory ``User`` DTO and called ``_save_users()``. The async
    version delegates to ``UserRepository.rotate_session`` which
    generates a new jti, stamps the 5 fields, and commits in a single
    UPDATE.
    """
    orm = await UserRepository.rotate_session(user.id, ip=ip, user_agent=user_agent)
    if orm is None:
        raise ValueError(f"_rotate_session_for: user {user.id} not found")
    # Refresh the DTO with the new session fields.
    user.active_session_id = orm.active_session_id
    user.active_session_ip = orm.active_session_ip
    user.active_session_user_agent = orm.active_session_user_agent
    user.active_session_started_at = (
        orm.active_session_started_at.isoformat()
        if orm.active_session_started_at else None
    )
    user.last_login = (
        orm.last_login.isoformat() if orm.last_login else None
    )
    return orm.active_session_id


async def _issue_token(user: User, ip: str = "", user_agent: str = "") -> dict:
    """Create a JWT and return the standard login response payload.

    Rotates the user's active session (single-session enforcement,
    Fix #34) so any previously-issued token for this user is
    invalidated atomically with the new token mint, and publishes a
    ``session_kicked`` event on the session_bus so any open SSE
    stream on the old session is notified.

    Async (Fix #35): ``_rotate_session_for`` is now async (it hits
    the SQLAlchemy ``users`` table).
    """
    jti = await _rotate_session_for(user, ip=ip, user_agent=user_agent)
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(hours=24),
        jti=jti,
    )
    session_bus.publish(user.id, {
        "type": "session_kicked",
        "reason": "new_login",
        "new_session_started_at": user.active_session_started_at,
    })
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    }


# ---------------------------------------------------------------------------
# Google SSO
# ---------------------------------------------------------------------------

@router.get("/sso/google")
async def google_sso_initiate():
    """Initiate Google OAuth2 flow — returns redirect URL."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google SSO is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    state = secrets.token_urlsafe(32)
    _pending_states[state] = "google"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _build_redirect_uri("google"),
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    redirect_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"redirect_url": redirect_url, "state": state}


@router.get("/sso/google/callback")
async def google_sso_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Google OAuth2 callback — exchange code for tokens & log in."""
    # Validate state
    if state not in _pending_states or _pending_states.pop(state) != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter.",
        )

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google SSO is not configured.",
        )

    # Exchange authorization code for tokens
    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": _build_redirect_uri("google"),
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error("Google token exchange failed: %s", token_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Google.",
        )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access_token in Google response.",
        )

    # Fetch user profile
    async with httpx.AsyncClient(timeout=30) as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error("Google userinfo fetch failed: %s", userinfo_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from Google.",
        )

    profile = userinfo_resp.json()
    email = profile.get("email")
    name = profile.get("name", email)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google account has no email address.",
        )

    # Auto-create or retrieve user
    user = await _auto_create_or_get_user(email=email, name=name, provider="google")
    log_audit_event("sso_login", user.username, "google_sso_login", resource=f"user:{user.id}", success=True)
    # Kick any prior local session for this user (Fix #34). SSO from
    # a new browser counts as a 2nd-device login.
    session_bus.publish(user.id, {
        "type": "session_kicked",
        "reason": "sso_login",
        "new_session_started_at": user.active_session_started_at,
    })
    return await _issue_token(user, ip=_client_ip(request), user_agent=_user_agent(request))


# ---------------------------------------------------------------------------
# Microsoft SSO
# ---------------------------------------------------------------------------

@router.get("/sso/microsoft")
async def microsoft_sso_initiate():
    """Initiate Microsoft OAuth2 flow — returns redirect URL."""
    if not MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft SSO is not configured. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.",
        )

    state = secrets.token_urlsafe(32)
    _pending_states[state] = "microsoft"

    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "redirect_uri": _build_redirect_uri("microsoft"),
        "scope": "openid email profile User.Read",
        "response_type": "code",
        "state": state,
        "response_mode": "query",
    }
    redirect_url = f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"
    return {"redirect_url": redirect_url, "state": state}


@router.get("/sso/microsoft/callback")
async def microsoft_sso_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Microsoft OAuth2 callback — exchange code for tokens & log in."""
    # Validate state
    if state not in _pending_states or _pending_states.pop(state) != "microsoft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter.",
        )

    if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft SSO is not configured.",
        )

    # Exchange authorization code for tokens
    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            MICROSOFT_TOKEN_URL,
            data={
                "code": code,
                "client_id": MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "redirect_uri": _build_redirect_uri("microsoft"),
                "grant_type": "authorization_code",
                "scope": "openid email profile User.Read",
            },
        )

    if token_resp.status_code != 200:
        logger.error("Microsoft token exchange failed: %s", token_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Microsoft.",
        )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access_token in Microsoft response.",
        )

    # Fetch user profile from Microsoft Graph
    async with httpx.AsyncClient(timeout=30) as client:
        graph_resp = await client.get(
            MICROSOFT_GRAPH_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if graph_resp.status_code != 200:
        logger.error("Microsoft Graph /me fetch failed: %s", graph_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from Microsoft Graph.",
        )

    profile = graph_resp.json()
    email = profile.get("mail") or profile.get("userPrincipalName")
    name = profile.get("displayName", email)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Microsoft account has no email address.",
        )

    # Auto-create or retrieve user
    user = await _auto_create_or_get_user(email=email, name=name, provider="microsoft")
    log_audit_event("sso_login", user.username, "microsoft_sso_login", resource=f"user:{user.id}", success=True)
    session_bus.publish(user.id, {
        "type": "session_kicked",
        "reason": "sso_login",
        "new_session_started_at": user.active_session_started_at,
    })
    return await _issue_token(user, ip=_client_ip(request), user_agent=_user_agent(request))


# ---------------------------------------------------------------------------
# SSO status
# ---------------------------------------------------------------------------

@router.get("/sso/status")
async def sso_status():
    """Check which SSO providers are configured."""
    return {
        "google": {
            "configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "client_id_set": bool(GOOGLE_CLIENT_ID),
            "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        },
        "microsoft": {
            "configured": bool(MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET),
            "client_id_set": bool(MICROSOFT_CLIENT_ID),
            "client_secret_set": bool(MICROSOFT_CLIENT_SECRET),
        },
    }


@router.get("/sso/me-status")
async def sso_me_status(user: User = Depends(require_authentication)):
    """Check which SSO providers the current user has linked."""
    from routes.integration_helpers import get_integration_config
    sso_config = await get_integration_config(user.id, "sso")
    linked = sso_config.get("config", {}).get("providers", [])
    return {
        "linked_providers": linked,
        "google": "google" in linked,
        "microsoft": "microsoft" in linked,
    }