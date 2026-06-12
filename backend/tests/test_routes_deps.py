"""
Tests for backend/routes/deps.py — the auth dependencies that every
authenticated route in the FastAPI app pulls in.

The deps module is the single source of truth for "does this request
have a valid user?" — every authenticated route in routes/*.py
imports `require_authentication` from here. A bug here would
silently break auth across the entire app surface.

We test:
- get_token_from_request: extracts Bearer token, returns None for
  no/malformed headers
- require_authentication: 401 for missing token, 401 for invalid
  token, returns User for valid token
- require_admin: 403 for non-admin User, returns user for admin

We mint real tokens via user_manager.create_user() +
create_access_token() rather than HTTP flow (the conftest's
`from main import app` is broken per Fix #31 — documented in
[[fix-31-user-id-auth-collision]]).
"""

import os
import sys
from unittest.mock import patch

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

from routes.deps import (
    get_token_from_request,
    require_authentication,
    require_admin,
)
from security.auth import User, create_access_token, user_manager


class TestGetTokenFromRequest:
    """Extract Bearer token from HTTPAuthorizationCredentials."""

    @pytest.mark.asyncio
    async def test_returns_token_when_credentials_present(self):
        # Mock the HTTPAuthorizationCredentials object that FastAPI
        # would inject. We don't need a real Request — the dependency
        # only looks at `credentials.credentials`.
        class FakeCreds:
            credentials = "abc123"

        result = await get_token_from_request(credentials=FakeCreds())
        assert result == "abc123"

    @pytest.mark.asyncio
    async def test_returns_none_when_credentials_missing(self):
        result = await get_token_from_request(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_credentials_empty(self):
        class FakeCreds:
            credentials = ""

        result = await get_token_from_request(credentials=FakeCreds())
        # Empty string is falsy — the require_authentication dep
        # treats this as "no token" (sees `not token` is True).
        assert result == ""


class TestRequireAuthentication:
    """401 with WWW-Authenticate: Bearer when token is missing/invalid."""

    @pytest.mark.asyncio
    async def test_raises_401_when_token_missing(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_authentication(token=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
        assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_raises_401_when_token_empty(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_authentication(token="")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_token_invalid(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_authentication(token="not-a-real-jwt")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"

    @pytest.mark.asyncio
    async def test_returns_user_when_token_valid(self):
        # Mint a real token via the same flow get_current_user() reads.
        # user_manager.create_user() persists to backend/data/users.json
        # (in .gitignore, but it exists on disk after the first
        # backend run — if it doesn't, user_manager will create it).
        import uuid

        username = f"deps_test_{uuid.uuid4().hex[:8]}"
        email = f"{username}@example.com"
        password = "TestPass123!"

        user = user_manager.create_user(
            username=username, email=email, password=password
        )
        assert user is not None, "user_manager.create_user() returned None"

        # Stamp the jti on the user so single-session enforcement
        # (Fix #34) accepts the token. Without this, a jti-bearing
        # token whose user has no active_session_id is rejected as a
        # post-logout token.
        jti = str(uuid.uuid4())
        user.active_session_id = jti
        user_manager._save_users()

        token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            jti=jti,
        )
        result = await require_authentication(token=token)
        assert result is not None
        assert result.id == user.id
        assert result.username == user.username


class TestRequireAdmin:
    """Admin gate: 403 unless user.is_admin is True."""

    @pytest.mark.asyncio
    async def test_raises_403_for_non_admin_user(self):
        from fastapi import HTTPException

        # We don't need a real user in the DB for this test —
        # require_admin only inspects `user.is_admin`, and the
        # upstream require_authentication dep is what would have
        # loaded the user. Bypass it with a User stub.
        non_admin = User(
            id="u1",
            username="alice",
            email="alice@example.com",
            is_admin=False,
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=non_admin)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_returns_user_for_admin(self):
        admin = User(
            id="u2",
            username="root",
            email="root@example.com",
            is_admin=True,
        )
        result = await require_admin(user=admin)
        assert result is admin


class TestStateModuleFlags:
    """The module-availability flags default to False; main.py flips
    them on at startup. A bug here would break the optional-feature
    detection in /health/modules."""

    def test_database_available_defaults_false(self):
        from routes import deps
        # We may have flipped this True during other tests; reload
        # the module to get a fresh import.
        import importlib
        importlib.reload(deps)
        assert deps.DATABASE_AVAILABLE is False

    def test_cognitive_graph_available_defaults_false(self):
        from routes import deps
        import importlib
        importlib.reload(deps)
        assert deps.COGNITIVE_GRAPH_AVAILABLE is False

    def test_all_optional_module_flags_default_false(self):
        from routes import deps
        import importlib
        importlib.reload(deps)
        for flag in [
            "DATABASE_AVAILABLE",
            "COGNITIVE_GRAPH_AVAILABLE",
            "WHISPER_AVAILABLE",
            "INTERVIEW_SIMULATOR_AVAILABLE",
            "JOB_TRACKER_AVAILABLE",
            "RESUME_REVIEW_AVAILABLE",
            "VOICE_CLONE_AVAILABLE",
            "RVC_GALLERY_AVAILABLE",
            "COLLABORATION_AVAILABLE",
        ]:
            assert getattr(deps, flag) is False, f"{flag} should default to False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
