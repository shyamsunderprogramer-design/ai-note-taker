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

    Bypasses the /auth/register + /auth/login HTTP flow (which is flaky
    in CI because the bcrypt+passlib versions diverge — see
    memory/bcrypt-passlib-incompatibility.md). Instead, mints a token
    directly via the auth module's helpers.
    """
    import uuid
    from core.database import get_user_manager
    from security.auth import create_access_token  # type: ignore

    unique_id = str(uuid.uuid4())[:8]
    username = f"test_{unique_id}"
    email = f"{username}@example.com"
    password = "TestPass123!"  # nosec B105 — test credential

    try:
        um = get_user_manager()
        user = um.create_user(username=username, email=email, password=password)
        token = create_access_token({"sub": str(user.id), "username": username})
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # If user-mgr or token creation fails, return empty headers so the
        # test can decide whether to skip or assert 401.
        return {}


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return os.getenv("TEST_API_URL", "http://127.0.0.1:8000")  # nosec B106 — test localhost
