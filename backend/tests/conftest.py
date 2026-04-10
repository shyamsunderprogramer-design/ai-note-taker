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

# Add backend and modules paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules', 'ai'))


@pytest.fixture(scope="session")
def test_client():
    """Provide a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    # Import main after env vars are set
    try:
        from main import app
        with TestClient(app) as client:
            yield client
    except ImportError as e:
        pytest.skip(f"Could not import app: {e}")


@pytest.fixture
def auth_headers(test_client):
    """Get authorization headers with a valid test token."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    username = f"test_{unique_id}"
    email = f"{username}@example.com"
    password = "TestPass123!"

    # Register using Form data (matching the /auth/register endpoint)
    test_client.post("/auth/register", data={
        "username": username,
        "email": email,
        "password": password
    })

    # Login using Form data (matching the /auth/login endpoint)
    response = test_client.post("/auth/login", data={
        "username": username,
        "password": password
    })

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    return {}


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
