"""
Regression test for Fix #31 — `/agents/sessions` and `/shadow/start` must
pull `user_id` from the auth dependency, not a hardcoded "default".

The original routes (in `routes/agents.py` — the live handler, NOT the
dead-code duplicates in `core/main.py`) had:

    @router.post("/agents/sessions")
    async def create_agent_session(...):
        ...
        session = await session_manager.create_session(
            user_id="default",
            ...
        )

This silently created every agent session under a single shared "default"
user identity, so two users running the agent at the same time would
overwrite each other's transcripts and suggestions. The fix adds
`user: User = Depends(require_authentication)` and uses `str(user.id)`.

These tests come in two flavors:

1. **AST-level regression** — parse `routes/agents.py` as AST and check
   the two endpoints have the right signature + no hardcoded "default"
   string literal in the create_session call. Catches the bug at the
   source-code level without needing a live server.

2. **Behavioral test** — spin up the FastAPI app in-process via
   httpx + ASGITransport, mint a JWT for a fake user, and hit the route
   to confirm (a) unauthenticated requests get 401, and (b) authenticated
   requests pass the caller's user_id to session_manager.create_session
   (not "default").
"""

import ast
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend/ to sys.path so `from core.main import app` resolves.
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

# Tests are sensitive to env var defaults; set them up before app import.
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("TESTING", "true")

# The live handlers live in routes/agents.py (core/main.py also has the
# same-named endpoints, but they are dead code — see Fix #31 notes).
AGENTS_PY = os.path.join(_BACKEND, "routes", "agents.py")


# ---------------------------------------------------------------------------
# AST-level regression: catches the bug at the source-code level without
# needing a live server.
# ---------------------------------------------------------------------------
class TestFix31RouteShape:
    """Inspect routes/agents.py AST to confirm the two endpoints have
    the expected signature + body shape."""

    @pytest.fixture
    def agents_tree(self):
        with open(AGENTS_PY) as f:
            return ast.parse(f.read())

    @staticmethod
    def _find_endpoint(tree, func_name):
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
                return node
        return None

    def _find_depends_auth(self, endpoint):
        """Returns the ast.arg named 'user' if it has Depends(require_authentication)
        as its default; otherwise None."""
        # In Python's AST, defaults align to the TAIL of args.args — if there
        # are 7 args and 7 defaults, all args have defaults; if there are 7
        # args and 5 defaults, only args[2:] do.
        n_args = len(endpoint.args.args)
        n_defaults = len(endpoint.args.defaults)
        first_default_idx = n_args - n_defaults
        for i, arg in enumerate(endpoint.args.args):
            if arg.arg != "user":
                continue
            if i < first_default_idx:
                # No default for this arg.
                return None
            default = endpoint.args.defaults[i - first_default_idx]
            if (isinstance(default, ast.Call)
                    and isinstance(default.func, ast.Name)
                    and default.func.id == "Depends"
                    and default.args
                    and isinstance(default.args[0], ast.Name)
                    and default.args[0].id == "require_authentication"):
                return arg
        return None

    def test_agents_sessions_has_auth_dependency(self, agents_tree):
        endpoint = self._find_endpoint(agents_tree, "create_agent_session")
        assert endpoint is not None, "create_agent_session not found in routes/agents.py"
        user_arg = self._find_depends_auth(endpoint)
        assert user_arg is not None, (
            "create_agent_session missing `user: User = Depends(require_authentication)` "
            "kwarg — Fix #31 regressed?"
        )

    def test_agents_sessions_does_not_hardcode_default_user(self, agents_tree):
        endpoint = self._find_endpoint(agents_tree, "create_agent_session")
        assert endpoint is not None
        for node in ast.walk(endpoint):
            if isinstance(node, ast.Constant) and node.value == "default":
                pytest.fail(
                    "create_agent_session still contains the string literal "
                    "'default' — Fix #31 regressed? Look for user_id=\"default\" "
                    "in the route body."
                )

    def test_shadow_start_has_auth_dependency(self, agents_tree):
        endpoint = self._find_endpoint(agents_tree, "start_shadow_interview")
        assert endpoint is not None, "start_shadow_interview not found in routes/agents.py"
        user_arg = self._find_depends_auth(endpoint)
        assert user_arg is not None, (
            "start_shadow_interview missing `user: User = Depends(require_authentication)` "
            "kwarg — Fix #31 regressed?"
        )

    def test_shadow_start_does_not_hardcode_default_user(self, agents_tree):
        endpoint = self._find_endpoint(agents_tree, "start_shadow_interview")
        assert endpoint is not None
        for node in ast.walk(endpoint):
            if isinstance(node, ast.Constant) and node.value == "default":
                pytest.fail(
                    "start_shadow_interview still contains the string literal "
                    "'default' — Fix #31 regressed?"
                )


# ---------------------------------------------------------------------------
# Behavioral test: hit the actual route through httpx + ASGI and confirm
# (a) the user_id passed to session_manager.create_session is the authenticated
# user's id, not "default", and (b) unauthenticated requests get 401.
# ---------------------------------------------------------------------------
class TestFix31AuthBehavior:
    """End-to-end: authenticate, POST /agents/sessions, confirm the
    session was created under the caller's user_id. Then POST without
    a token and confirm 401."""

    @pytest.fixture
    def fake_user_id(self):
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_agents_sessions_uses_authenticated_user_id(self, fake_user_id):
        from core.main import app
        from httpx import ASGITransport, AsyncClient
        from security.auth import user_manager, create_access_token

        captured = {"user_id": None}

        async def fake_create_session(**kwargs):
            captured["user_id"] = kwargs.get("user_id")
            return {"id": "test-session-id", **kwargs}

        stub_manager = MagicMock()
        stub_manager.create_session = AsyncMock(side_effect=fake_create_session)

        # Create a real user in the user_manager's JSON file, then mint
        # a JWT for that user. This is the same flow /auth/login would
        # follow but bypasses the HTTP layer (which the conftest's
        # `from main import app` does not resolve).
        unique_id = fake_user_id[:8]
        username = f"fix31_{unique_id}"
        email = f"{username}@example.com"
        password = "TestPass123!"  # nosec B105 — test credential
        user = user_manager.create_user(username=username, email=email, password=password)
        token = create_access_token({"sub": str(user.id), "username": user.username})

        with patch("routes.agents.AGENTS_AVAILABLE", True), \
             patch("routes.agents.session_manager", stub_manager):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/agents/sessions?session_type=meeting&active_agents=meeting",
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
        assert captured["user_id"] is not None, "session_manager.create_session was not called"
        assert captured["user_id"] != "default", (
            f"user_id should NOT be 'default' — Fix #31 has regressed. "
            f"Got {captured['user_id']!r}."
        )
        # The user_id should match the authenticated user's id (as a string).
        assert captured["user_id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_agents_sessions_rejects_unauthenticated(self):
        """No token → 401. Confirms require_authentication is wired in."""
        from core.main import app
        from httpx import ASGITransport, AsyncClient

        with patch("routes.agents.AGENTS_AVAILABLE", True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/agents/sessions?session_type=meeting")

        # 401 if require_authentication is wired in; 200 if the route
        # is unauthenticated. The fix requires the former.
        assert resp.status_code == 401, (
            f"expected 401 for unauthenticated request, got {resp.status_code}. "
            f"If 200, the require_authentication dependency is missing — Fix #31 regressed."
        )

    @pytest.mark.asyncio
    async def test_shadow_start_rejects_unauthenticated(self):
        from core.main import app
        from httpx import ASGITransport, AsyncClient

        with patch("routes.agents.AGENTS_AVAILABLE", True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/shadow/start?company=Acme&role=Engineer&stage=phone",
                )

        assert resp.status_code == 401, (
            f"expected 401 for unauthenticated /shadow/start, got {resp.status_code}. "
            f"If 200, the require_authentication dependency is missing — Fix #31 regressed."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
