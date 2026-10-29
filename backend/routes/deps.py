"""
Shared dependencies for route modules.

Centralizes access to application state, authentication, and commonly
needed singletons so route modules don't import from main.py.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from security import get_current_user
from security.auth import User


# ── Application State ───────────────────────────────────────────────────────
# Set by main.py at startup via deps.state = <AppState instance>.
# Route modules access state via:  from routes.deps import state

state = None  # Will be replaced with AppState instance at startup


# ── Authentication Dependencies ──────────────────────────────────────────────

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> str:
    """Extract Bearer token from Authorization header."""
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)) -> User:
    """Dependency: require a valid authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: User = Depends(require_authentication)) -> User:
    """Dependency: require an admin user."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def resolve_user_id(user: User, supplied: Optional[str]) -> str:
    """Return the effective user_id for an endpoint (IDOR fix, Fix #31
    pattern).

    The authenticated user is always the source of truth. A client may
    pass its own id (back-compat for callers built before the fix), the
    literal ``"me"`` (for clients that never learn their own id, such
    as the web dashboards), or omit it; passing anyone else's id is
    rejected with 403 so a client can never read or write another
    user's data by guessing ids.
    """
    if supplied is None or supplied == "me":
        return str(user.id)
    if supplied != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's data",
        )
    return supplied


# ── Module Availability Flags ────────────────────────────────────────────────
# These are set by main.py during startup based on which modules loaded.

DATABASE_AVAILABLE = False
COGNITIVE_GRAPH_AVAILABLE = False
WHISPER_AVAILABLE = False
INTERVIEW_SIMULATOR_AVAILABLE = False
JOB_TRACKER_AVAILABLE = False
RESUME_REVIEW_AVAILABLE = False
VOICE_CLONE_AVAILABLE = False
RVC_GALLERY_AVAILABLE = False
COLLABORATION_AVAILABLE = False