"""
Test configuration and fixtures for AI Note Taker backend tests.
"""
import os
import sys
import pytest
import pytest_asyncio

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


@pytest_asyncio.fixture
async def auth_headers(test_client):
    """Get authorization headers with a valid test token.

    Mints a real user in the user_manager and a real access+refresh
    pair sharing a single jti (Fix #34 single-session enforcement).
    The jti is also stamped on the user so the verify_token jti
    check passes — without it, a jti-bearing token whose user has
    no active_session_id is rejected as a post-logout token.

    Fix #35: this fixture is now async (the underlying
    ``user_manager.create_user`` and ``auth_headers_set_jti`` are
    async). It also uses the dedicated test-only
    ``UserRepository.auth_headers_set_jti`` helper (added in
    Commit 2) to stamp the jti, replacing the old
    ``user_manager._save_users()`` call which no longer exists.

    The fixture itself is ``@pytest_asyncio.fixture`` (not
    ``@pytest.fixture``) because the underlying user-mint helpers are
    async — the previous sync version called
    ``asyncio.get_event_loop().run_until_complete(...)`` which is
    forbidden when pytest-asyncio already has a loop running and is
    deprecated on Python 3.12 main thread.

    No try/except: if user creation or token minting fails, the
    fixture should raise so the test fails loudly. The original
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
    from core.database import UserRepository

    unique_id = str(uuid.uuid4())[:8]
    username = f"test_{unique_id}"
    email = f"{username}@example.com"
    password = "TestPass123!"  # nosec B105 — test credential

    user = await user_manager.create_user(
        username=username, email=email, password=password
    )
    # The user has no active_session_id yet (we just created them
    # and never went through /auth/login). For fixture purposes,
    # mint a jti and stamp it via the test-only repo helper so the
    # jti check passes.
    jti = str(uuid.uuid4())
    await UserRepository.auth_headers_set_jti(str(user.id), jti)
    access = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        jti=jti,
    )
    return {"Authorization": f"Bearer {access}"}


@pytest_asyncio.fixture
async def tmp_db(monkeypatch, tmp_path):
    """Per-test SQLite database with the SA schema applied.

    Sets up a fresh ``data/test_<uuid>.db`` for the test, re-resolves
    the module-level ``DATABASE_URL`` / ``db_manager._initialized``,
    and yields the path. The previous conftest had no per-test DB
    setup, which meant tests that called ``user_manager.create_user``
    were actually writing to the dev DB. Fix #35 Commit 4: tests
    that touch the user store need a hermetic DB.
    """
    import os as _os
    from core import database

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("FORCE_SQLITE", "true")
    monkeypatch.setenv("ANT_SKIP_ALEMBIC", "1")

    # Re-resolve module-level URL + reset manager.
    database.DATABASE_URL = _os.environ["DATABASE_URL"]
    database.USE_SQLITE = True
    database.FORCE_SQLITE = True
    database.db_manager.engine = None
    database.db_manager.session_maker = None
    database.db_manager._initialized = False

    await database.db_manager.initialize()
    try:
        yield db_path
    finally:
        await database.db_manager.close()
        database.db_manager.engine = None
        database.db_manager.session_maker = None
        database.db_manager._initialized = False
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return os.getenv("TEST_API_URL", "http://127.0.0.1:8000")  # nosec B106 — test localhost
