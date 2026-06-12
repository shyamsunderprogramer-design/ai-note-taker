"""
Route module for the 15 endpoints that were unique to main.py at the
end of the 2026-06-05 audit (Fix #4). Each handler here was moved
verbatim from backend/core/main.py and the inline @app.X decorator
on the duplicate in main.py is now commented out (the live handler
is here).

Endpoints owned by this module:
  GET  /                          (root — also defined in routes/health.py
                                    as a duplicate, but that one is at
                                    /health, the canonical root is here)
  GET  /health/config             (DB config diagnostic)
  GET  /health/db-debug           (DB connection diagnostic)
  GET  /auth/status               (frontend check)
  GET  /auth/debug/users          (debug-only user store dump)
  POST /auth/forgot-password      (password reset step 1)
  POST /auth/set-security-question (set security Q for authed user)
  POST /voice-agent/start
  POST /voice-agent/stop
  GET  /voice-agent/status
  WS   /ws/voice-agent            (declared in routes/voice_agent.py
                                    because routers don't host WS
                                    handlers cleanly)
  GET  /mcp/status                (declared in routes/mcp.py)
  POST /mcp/tools/{tool_name}     (declared in routes/mcp.py)
  GET  /mcp/tools                 (declared in routes/mcp.py)
  GET  /mcp/resources             (declared in routes/mcp.py)

This file is the catch-all for the 9 HTTP endpoints that fit no other
route module. The voice-agent and mcp routers live in their own files
because they have WebSocket / larger handler bodies that benefit from
isolation.
"""
import logging
import os
import re

from fastapi import APIRouter, Depends, Form, HTTPException, WebSocket

from security import (
    InputValidator, ErrorCode, error_response, rate_limit, log_audit_event,
)
from security.auth import user_manager, User
from security import get_current_user

# Local require_authentication (mirrors the pattern in routes/auth.py,
# routes/admin.py, routes/agents.py — duplicated rather than imported
# to avoid circular deps)
import os
from fastapi import status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends as _Depends

_security_bearer = HTTPBearer(auto_error=False)

# AUTH_REQUIRED is defined in core/main.py — re-read it from the env to
# avoid an import cycle. Same logic: case-insensitive, defaults to True.
_AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = _Depends(_security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = _Depends(get_token_from_request)):
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
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

logger = logging.getLogger("routes.main_unique")

router = APIRouter()

# App-state dependency (set by main.py at include time)
from routes import deps as _route_deps  # noqa: E402


# ── Root + health diagnostics ──────────────────────────────────────────
@router.get("/")
def health_check():
    """Root health probe — returns service + mode info."""
    state = getattr(_route_deps, "state", None)
    mode = state.current_mode if state else "auto"
    return {
        "status": "ok",
        "service": "ai-backend",
        "mode": mode,
        "security": {
            "authentication": "enabled",
            "rate_limiting": "enabled",
            "https_required": False,  # Set to True when SSL is configured
        },
    }


@router.get("/health/config")
def config_check():
    """Diagnostic endpoint to verify database configuration (no secrets exposed)."""
    from core.database import (
        DATABASE_URL as db_url,
        USE_SQLITE, FORCE_SQLITE, DEFAULT_SQLITE_URL,
        HAS_SQLALCHEMY, db_manager,
    )
    _redacted = re.sub(r'://[^@]+@', '://***@', db_url) if db_url else "(none)"
    _db_type = (
        "sqlite" if "sqlite" in db_url.lower()
        else "postgresql" if "postgresql" in db_url.lower()
        else "unknown"
    )
    return {
        "database_url_prefix": db_url[:40] + "..." if db_url and len(db_url) > 40 else _redacted,
        "database_type": _db_type,
        "use_sqlite": USE_SQLITE,
        "force_sqlite": FORCE_SQLITE,
        "cloud_mode": os.getenv("CLOUD_MODE", "false"),
        "database_available": HAS_SQLALCHEMY,
        "db_initialized": db_manager._initialized if db_manager else False,
        "has_engine": db_manager.engine is not None if db_manager else False,
        "default_sqlite_path": str(DEFAULT_SQLITE_URL)[:60],
    }


@router.get("/health/db-debug")
async def db_debug():
    """Diagnostic endpoint that attempts a fresh database connection and returns the error."""
    from core.database import DATABASE_URL as db_url, HAS_SQLALCHEMY
    if not HAS_SQLALCHEMY:
        return {"error": "SQLAlchemy not available"}
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        _redacted = re.sub(r'://[^@]+@', '://***@', db_url) if db_url else "(none)"
        _is_sqlite = "sqlite" in db_url.lower()
        _test_url = db_url
        _engine_kwargs = {"echo": False}
        if not _is_sqlite:
            # PostgreSQL: strip sslmode from URL, add SSL context
            import ssl as _ssl
            _ssl_ctx = _ssl.create_default_context()
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = _ssl.CERT_NONE
            if "sslmode=" in _test_url:
                _test_url = _test_url.split("?sslmode=")[0]
                if _test_url.endswith("?"):
                    _test_url = _test_url[:-1]
            _engine_kwargs["pool_size"] = 1
            _engine_kwargs["connect_args"] = {"ssl": _ssl_ctx}
        engine = create_async_engine(_test_url, **_engine_kwargs)
        if _is_sqlite:
            query = text("SELECT sqlite_version()")
        else:
            query = text("SELECT version()")
        async with engine.begin() as conn:
            result = await conn.execute(query)
            version = result.scalar()
        await engine.dispose()
        return {
            "status": "connected",
            "version": version,
            "url": _redacted,
            "dialect": "sqlite" if _is_sqlite else "postgresql",
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "url": re.sub(r'://[^@]+@', '://***@', db_url) if db_url else "(none)",
        }


# ── Auth (3 endpoints unique to main.py) ───────────────────────────────
@router.get("/auth/status")
async def auth_status():
    """Returns whether authentication is required. Frontend uses this
    to decide whether to show the login screen."""
    return {"auth_required": _AUTH_REQUIRED}


# NOTE: ``GET /auth/debug/users`` was removed in Fix #35 Commit 3. It
# was a temporary debug endpoint that returned the in-memory user
# dict. The user store is now the SQLAlchemy ``users`` table — use
# ``POST /admin/users`` (or a dev tool) to inspect users. Keeping a
# debug endpoint that enumerates usernames on the public API was a
# small enumeration-attack surface, even with auth required.


@router.post("/auth/forgot-password")
@rate_limit(requests_per_minute=3)
async def forgot_password(username: str = Form(...)):
    """Step 1 of password reset: look up user's security question.
    Always returns 200 to prevent username enumeration."""
    question = await user_manager.has_security_question(username)
    if question:
        return {
            "status": "success",
            "security_question": question,
            "has_security_question": True,
        }
    return {
        "status": "success",
        "security_question": None,
        "has_security_question": False,
        "message": "If this account exists and has a security question set, it will be shown.",
    }


@router.post("/auth/set-security-question")
async def set_security_question_endpoint(
    user: User = Depends(require_authentication),
    security_question: str = Form(...),
    security_answer: str = Form(...),
):
    """Set or update the security question for the authenticated user."""
    valid_question = InputValidator.validate_security_question(security_question)
    valid_answer = InputValidator.validate_security_answer(security_answer)
    if not valid_question:
        raise HTTPException(status_code=400, detail="Security question must be 5-200 characters")
    if not valid_answer:
        raise HTTPException(status_code=400, detail="Security answer must be 2-100 characters")
    await user_manager.set_security_question(user.username, valid_question, valid_answer)
    return {"status": "success", "message": "Security question set successfully"}
