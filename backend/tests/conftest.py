"""
Test configuration and fixtures for AI Note Taker backend tests.
"""
import os
import sys
import pytest

# Set test environment variables before importing app modules
os.environ["USE_SQLITE"] = "true"
os.environ["AUTH_REQUIRED"] = "false"  # Disable auth middleware for most tests
os.environ["TESTING"] = "true"
os.environ["ANT_SKIP_ALEMBIC"] = "1"  # tests build a fresh in-memory DB

# Add backend and modules paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules', 'ai'))


@pytest.fixture(scope="session")
def test_client():
    """Provide a test client for the FastAPI app.

    Imports `core.main.app` lazily so the heavy ML/Neo4j imports don't
    block collection. If the import fails (e.g., missing optional dep),
    the fixture skips the test rather than erroring the whole session.
    """
    from fastapi.testclient import TestClient
    try:
        from core.main import app  # canonical path, matches core/start_server.py
        with TestClient(app) as client:
            yield client
    except ImportError as e:
        pytest.skip(f"Could not import app: {e}")


@pytest.fixture
def auth_headers(test_client):
    """Get authorization headers with a valid test token.

    Mints a real user in the user_manager and a real access+refresh
    pair sharing a single jti (Fix #34 single-session enforcement).
    The jti is also stamped on the user so the verify_token jti
    check passes — without it, a jti-bearing token whose user has
    no active_session_id is rejected as a post-logout token.

    No try/except: if user creation or token minting fails, the
    fixture should raise so the test fails loudly. The previous
    version of this fixture silently swallowed the ImportError
    for ``get_user_manager`` (which doesn't exist) and returned
    ``{}`` for ``Authorization``, meaning every auth-touching test
    in CI was running unauthenticated. See
    https://.../conftest-import-bug for the post-mortem.
    """
    import uuid
    from security.auth import (
        user_manager, create_access_token,
    )

    unique_id = str(uuid.uuid4())[:8]
    username = f"test_{unique_id}"
    email = f"{username}@example.com"
    password = "TestPass123!"  # nosec B105 — test credential

    user = user_manager.create_user(username=username, email=email, password=password)
    # The user has no active_session_id yet (we just created them
    # and never went through /auth/login). For fixture purposes,
    # mint a jti and stamp it so the jti check passes.
    jti = str(uuid.uuid4())
    user.active_session_id = jti
    user_manager._save_users()

    access = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        jti=jti,
    )
    return {"Authorization": f"Bearer {access}"}


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return os.getenv("TEST_API_URL", "http://127.0.0.1:8000")  # nosec B106 — test localhost
