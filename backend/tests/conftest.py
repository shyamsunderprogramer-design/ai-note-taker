"""
Test configuration and fixtures for AI Note Taker backend tests.
"""
import os
import sys
import pytest

# Set test environment variables before importing app modules
os.environ["USE_SQLITE"] = "true"
os.environ["AUTH_REQUIRED"] = "false"  # Disable auth for most tests
os.environ["TESTING"] = "true"


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
    # Try to register and login a test user
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    email = f"test_{unique_id}@example.com"
    password = "TestPass123!"

    # Register
    test_client.post("/auth/register", json={
        "email": email,
        "password": password
    })

    # Login
    response = test_client.post("/auth/login", json={
        "email": email,
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
