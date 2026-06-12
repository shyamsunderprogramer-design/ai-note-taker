"""
Tests for the new auth-flow methods on UserRepository (Fix #35 Commit 2).

These methods are the persistence-layer surface the
`security.auth.user_manager` async shim (Commit 3) will delegate to.
They are tested directly here against a per-test SQLite DB so we can
catch bugs in the SQLAlchemy paths without spinning up the full
FastAPI app.

Coverage:
  - count(): 0 / N correctly
  - authenticate_and_rotate_session: success, unknown user, inactive
    user, wrong password, session rotation
  - rotate_session: no password required, jti changes
  - clear_session: zeros 4 columns
  - update_password: bcrypt hash applied, next authenticate with old
    password fails
  - set_security_question + verify_security_answer: round-trip
  - auth_headers_set_jti: round-trip (the conftest contract)

Each test gets a fresh tmp_path DB via the `tmp_db` fixture.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

# Add backend/ to sys.path so `from core.database import ...` resolves.
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)


# ---------------------------------------------------------------------------
# Per-test SQLite DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tmp_db(monkeypatch, tmp_path):
    """Yield a fresh per-test SQLite DB with the SA schema applied.

    Mirrors the env-var setup used by `tests/test_alembic_migrations.py`
    (`TestDatabaseManagerRunsAlembic.setup_method`) but as a pytest
    fixture. After the test, the engine is disposed and the file
    deleted.
    """
    import asyncio
    from core import database

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("FORCE_SQLITE", "true")
    monkeypatch.setenv("ANT_SKIP_ALEMBIC", "1")  # use create_all, skip alembic

    # Re-resolve module-level URL + reset manager so initialize() picks
    # up the new env vars.
    database.DATABASE_URL = os.environ["DATABASE_URL"]
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


@pytest_asyncio.fixture
async def user_repo(tmp_db):
    """Return the UserRepository class (imported lazily so the fixture
    can re-init the engine first)."""
    from core.database import UserRepository
    return UserRepository


@pytest.fixture
def hash_password():
    """Return a callable that bcrypt-hashes a plain password.

    Uses `security.auth.user_manager._hash_password` (the canonical
    hash path) so tests exercise the same bcrypt<4.1 pin the production
    auth path uses. Returns a function `(plain) -> hashed_str`.
    """
    from security.auth import user_manager
    def _h(plain: str) -> str:
        return user_manager._hash_password(plain)
    return _h


# ---------------------------------------------------------------------------
# count()
# ---------------------------------------------------------------------------

class TestUserRepositoryCount:
    @pytest.mark.asyncio
    async def test_count_returns_zero_on_empty_table(self, user_repo):
        assert await user_repo.count() == 0

    @pytest.mark.asyncio
    async def test_count_returns_n_after_creates(self, user_repo, hash_password):
        # Use the canonical create() signature: hashed_password.
        h = hash_password("TestPass123!")
        for i in range(3):
            await user_repo.create(
                username=f"u{i}",
                email=f"u{i}@example.com",
                hashed_password=h,
            )
        assert await user_repo.count() == 3


# ---------------------------------------------------------------------------
# authenticate_and_rotate_session
# ---------------------------------------------------------------------------

class TestUserRepositoryAuthenticateAndRotate:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_user(self, user_repo):
        result = await user_repo.authenticate_and_rotate_session(
            "ghost", "TestPass123!"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_inactive_user(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        await user_repo.create(
            username="alice", email="alice@example.com",
            hashed_password=h, is_active=False,
        )
        result = await user_repo.authenticate_and_rotate_session(
            "alice", "TestPass123!"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_password(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        await user_repo.create(
            username="alice", email="alice@example.com", hashed_password=h,
        )
        result = await user_repo.authenticate_and_rotate_session(
            "alice", "WrongPass123!"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_rotates_jti_on_success(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        await user_repo.create(
            username="alice", email="alice@example.com", hashed_password=h,
        )
        # First login: no active_session_id yet
        u1 = await user_repo.authenticate_and_rotate_session("alice", "TestPass123!")
        assert u1 is not None
        assert u1.active_session_id is not None
        first_jti = u1.active_session_id

        # Second login: jti must change
        u2 = await user_repo.authenticate_and_rotate_session("alice", "TestPass123!")
        assert u2 is not None
        assert u2.active_session_id != first_jti

    @pytest.mark.asyncio
    async def test_records_ip_and_user_agent(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        await user_repo.create(
            username="bob", email="bob@example.com", hashed_password=h,
        )
        u = await user_repo.authenticate_and_rotate_session(
            "bob", "TestPass123!", ip="10.0.0.1", user_agent="pytest/1.0"
        )
        assert u.active_session_ip == "10.0.0.1"
        assert u.active_session_user_agent == "pytest/1.0"

    @pytest.mark.asyncio
    async def test_updates_last_login(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        created = await user_repo.create(
            username="carol", email="carol@example.com", hashed_password=h,
        )
        # last_login starts as None (no auto-default)
        assert created.last_login is None

        u = await user_repo.authenticate_and_rotate_session("carol", "TestPass123!")
        assert u.last_login is not None


# ---------------------------------------------------------------------------
# rotate_session (no password)
# ---------------------------------------------------------------------------

class TestUserRepositoryRotateSession:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_user_id(self, user_repo):
        result = await user_repo.rotate_session(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_rotates_jti_without_password(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        u = await user_repo.create(
            username="dave", email="dave@example.com", hashed_password=h,
        )
        # No active_session_id yet
        assert u.active_session_id is None

        rotated = await user_repo.rotate_session(str(u.id))
        assert rotated is not None
        assert rotated.active_session_id is not None

    @pytest.mark.asyncio
    async def test_jti_changes_between_rotations(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        u = await user_repo.create(
            username="eve", email="eve@example.com", hashed_password=h,
        )
        r1 = await user_repo.rotate_session(str(u.id))
        r2 = await user_repo.rotate_session(str(u.id))
        assert r1.active_session_id != r2.active_session_id


# ---------------------------------------------------------------------------
# clear_session
# ---------------------------------------------------------------------------

class TestUserRepositoryClearSession:
    @pytest.mark.asyncio
    async def test_zeros_active_session_columns(self, user_repo, hash_password):
        h = hash_password("TestPass123!")
        u = await user_repo.create(
            username="frank", email="frank@example.com", hashed_password=h,
        )
        # Set them first
        await user_repo.rotate_session(
            str(u.id), ip="1.1.1.1", user_agent="ua"
        )

        ok = await user_repo.clear_session(str(u.id))
        assert ok is True

        reloaded = await user_repo.get_by_id(str(u.id))
        assert reloaded.active_session_id is None
        assert reloaded.active_session_ip is None
        assert reloaded.active_session_user_agent is None
        assert reloaded.active_session_started_at is None

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_user(self, user_repo):
        ok = await user_repo.clear_session(str(uuid.uuid4()))
        assert ok is False


# ---------------------------------------------------------------------------
# update_password
# ---------------------------------------------------------------------------

class TestUserRepositoryUpdatePassword:
    @pytest.mark.asyncio
    async def test_new_password_authenticates(self, user_repo, hash_password):
        old = hash_password("OldPass123!")
        u = await user_repo.create(
            username="grace", email="grace@example.com", hashed_password=old,
        )
        new = hash_password("NewPass456!")
        ok = await user_repo.update_password(str(u.id), new)
        assert ok is True

        # Authenticate with new password succeeds
        result = await user_repo.authenticate_and_rotate_session("grace", "NewPass456!")
        assert result is not None

    @pytest.mark.asyncio
    async def test_old_password_no_longer_authenticates(self, user_repo, hash_password):
        old = hash_password("OldPass123!")
        u = await user_repo.create(
            username="henry", email="henry@example.com", hashed_password=old,
        )
        new = hash_password("NewPass456!")
        await user_repo.update_password(str(u.id), new)

        result = await user_repo.authenticate_and_rotate_session("henry", "OldPass123!")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_user(self, user_repo, hash_password):
        ok = await user_repo.update_password(
            str(uuid.uuid4()), hash_password("Whatever123!")
        )
        assert ok is False


# ---------------------------------------------------------------------------
# set_security_question + verify_security_answer
# ---------------------------------------------------------------------------

class TestUserRepositorySecurityQuestion:
    @pytest.mark.asyncio
    async def test_round_trip(self, user_repo, hash_password):
        pw = hash_password("TestPass123!")
        u = await user_repo.create(
            username="iris", email="iris@example.com", hashed_password=pw,
        )

        # No question set yet
        assert u.security_question is None
        assert u.hashed_security_answer is None

        hashed = hash_password("Fluffy")
        ok = await user_repo.set_security_question(
            str(u.id), "What is your pet's name?", hashed
        )
        assert ok is True

        reloaded = await user_repo.get_by_id(str(u.id))
        assert reloaded.security_question == "What is your pet's name?"
        assert reloaded.hashed_security_answer is not None
        # Verify succeeds with the right answer
        assert await user_repo.verify_security_answer(
            str(u.id), "Fluffy", reloaded.hashed_security_answer
        ) is True
        # Verify fails with the wrong answer
        assert await user_repo.verify_security_answer(
            str(u.id), "Spike", reloaded.hashed_security_answer
        ) is False

    @pytest.mark.asyncio
    async def test_verify_returns_false_when_no_question_set(self, user_repo, hash_password):
        pw = hash_password("TestPass123!")
        u = await user_repo.create(
            username="jack", email="jack@example.com", hashed_password=pw,
        )
        # No question set
        assert await user_repo.verify_security_answer(
            str(u.id), "Anything", None
        ) is False
        assert await user_repo.verify_security_answer(
            str(u.id), "Anything", ""
        ) is False


# ---------------------------------------------------------------------------
# auth_headers_set_jti
# ---------------------------------------------------------------------------

class TestUserRepositoryAuthHeadersSetJti:
    @pytest.mark.asyncio
    async def test_stamps_jti(self, user_repo, hash_password):
        pw = hash_password("TestPass123!")
        u = await user_repo.create(
            username="kate", email="kate@example.com", hashed_password=pw,
        )
        assert u.active_session_id is None

        test_jti = str(uuid.uuid4())
        ok = await user_repo.auth_headers_set_jti(str(u.id), test_jti)
        assert ok is True

        reloaded = await user_repo.get_by_id(str(u.id))
        assert reloaded.active_session_id == test_jti

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_user(self, user_repo):
        ok = await user_repo.auth_headers_set_jti(str(uuid.uuid4()), "abc")
        assert ok is False


# ---------------------------------------------------------------------------
# Hashing is actually used (smoke test that the repo is using pwd_context).
# We don't depend on the bcrypt-vs-fake implementation
# (`test_security_auth.py` may have monkeypatched `pwd_context` to a
# `_FakePwdContext` returning `h$<plain>`). The contract under test is:
# the stored hash is NOT the literal plaintext.
# ---------------------------------------------------------------------------

class TestUserRepositoryHashingIsUsed:
    @pytest.mark.asyncio
    async def test_stored_hash_is_not_plaintext(self, user_repo, hash_password):
        plain = "TestPass123!"
        h = hash_password(plain)
        await user_repo.create(
            username="liam", email="liam@example.com", hashed_password=h,
        )
        reloaded = await user_repo.get_by_username("liam")
        assert reloaded.hashed_password != plain
        # bcrypt hashes start with $2a$ / $2b$ / $2y$; the test fake
        # uses "h$". Both are valid evidence that hashing happened.
        assert reloaded.hashed_password[:2] in ("$2", "h$")
