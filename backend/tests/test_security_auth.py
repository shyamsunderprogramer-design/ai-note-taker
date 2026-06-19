"""
Test suite for backend/security/auth.py
Covers User dataclass (DTO), UserManager (async shim over UserRepository),
and the JWT access/refresh token issue/verify functions.

Fix #35: UserManager is now an async facade over core.database.UserRepository.
The JSON file store (USERS_FILE) and its _LEGACY_USERS_FILE are gone —
the SQLAlchemy ``users`` table is the single source of truth. Tests that
used to monkeypatch ``USERS_FILE`` / ``_LEGACY_USERS_FILE`` to point at
``tmp_path / "users.json"`` now use the ``tmp_db`` fixture (per-test
SQLite DB with the SA schema applied).

Run with: python -m pytest backend/tests/test_security_auth.py -v
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

# Add backend/ to sys.path so `from security.auth import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from security.auth import (  # noqa: E402
    User,
    TokenData,
    UserManager,
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_refresh_token,
    check_admin,
    HAS_JWT,
)


# ---------------------------------------------------------------------------
# Bcrypt+passlib compatibility shim.
#
# As of passlib 1.7.4 + bcrypt 4.x, passlib's internal `detect_wrap_bug`
# uses a 73-byte test secret to detect a 2011-era bug in old bcrypt
# versions. Modern bcrypt raises ValueError on >72-byte secrets instead
# of silently truncating, so passlib's startup probe crashes the entire
# import chain. This is a known upstream issue:
#   https://foss.heptapod.net/python-libs/passlib/-/issues/126
#
# We don't want these tests to depend on the bcrypt bug-detection path —
# we're testing UserManager's logic, not bcrypt's hash math. Patch
# pwd_context with a deterministic in-memory stand-in that has the
# same hash/verify contract. This lets the auth tests run on any
# combination of passlib/bcrypt without environmental pain.
# ---------------------------------------------------------------------------
class _FakePwdContext:
    """Minimal stand-in for passlib CryptContext that satisfies the
    `hash(password)` and `verify(password, hashed)` contract used by
    auth.py. Stores the plaintext wrapped in "h$" so we can detect
    tampering in verify()."""

    def hash(self, password: str) -> str:  # noqa: D401
        return f"h${password}"

    def verify(self, password: str, hashed: str) -> bool:  # noqa: D401
        if not hashed.startswith("h$"):
            return False
        return password == hashed[2:]


@pytest.fixture(autouse=True)
def _fake_pwd_context(monkeypatch):
    """Patch security.auth.pwd_context to _FakePwdContext for the test."""
    from security import auth as auth_module
    if auth_module.pwd_context is not None:
        monkeypatch.setattr(auth_module, "pwd_context", _FakePwdContext())


# ---------------------------------------------------------------------------
# Per-test SQLite DB fixture.
#
# Fix #35: the in-memory user dict is gone. Tests need a real DB.
# Mirrors the fixture in tests/test_user_repository_auth.py.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def tmp_db(monkeypatch, tmp_path):
    """Yield a fresh per-test SQLite DB with the SA schema applied.

    Re-resolves ``DATABASE_URL`` and resets the module-level
    ``db_manager._initialized`` so ``db_manager.initialize()`` builds
    a fresh engine against the tmp_path DB.
    """
    from core import database

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("FORCE_SQLITE", "true")
    monkeypatch.setenv("ANT_SKIP_ALEMBIC", "1")

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
async def user_manager(tmp_db):
    """Return a fresh UserManager (stateless now; just a shim)."""
    return UserManager()


# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------
class TestUserDataclass:
    def test_basic_construction(self):
        u = User(id="abc", username="alice", email="alice@example.com")
        assert u.username == "alice"  # nosec B101
        assert u.email == "alice@example.com"  # nosec B101
        assert u.is_active is True  # nosec B101
        assert u.is_admin is False  # nosec B101
        assert u.hashed_password is None  # nosec B101

    def test_default_quota_has_today_count_zero(self):
        u = User(id="abc", username="alice", email="alice@example.com")
        assert u.api_quota["requests_today"] == 0  # nosec B101
        assert u.api_quota["daily_limit"] == 1000  # nosec B101

    def test_created_at_is_iso_format(self):
        u = User(id="abc", username="alice", email="alice@example.com")
        # Should not raise — datetime.isoformat format
        datetime.fromisoformat(u.created_at)


# ---------------------------------------------------------------------------
# User.from_orm (Fix #35)
# ---------------------------------------------------------------------------
class TestUserFromOrm:
    """User.from_orm(orm_user) bridges an ORM row to the public DTO."""

    def test_id_is_stringified_uuid(self):
        from uuid import uuid4
        from security.auth import User
        # Fake ORM row with id as uuid.UUID
        class _FakeOrm:
            pass
        orm = _FakeOrm()
        orm.id = uuid4()
        orm.username = "alice"
        orm.email = "alice@example.com"
        orm.hashed_password = "h$pw"
        orm.is_active = True
        orm.is_admin = False
        orm.api_quota = {"requests_today": 0, "daily_limit": 1000, "reset_date": "2026-06-12"}
        orm.security_question = None
        orm.hashed_security_answer = None
        orm.active_session_id = None
        orm.active_session_ip = None
        orm.active_session_user_agent = None
        orm.active_session_started_at = None
        orm.on_new_login_pref = "auto_kick"
        orm.created_at = None
        orm.last_login = None

        dto = User.from_orm(orm)
        assert isinstance(dto.id, str)  # nosec B101
        assert dto.id == str(orm.id)  # nosec B101
        assert dto.username == "alice"  # nosec B101

    def test_handles_datetime_orm_fields(self):
        from datetime import datetime, timezone
        from security.auth import User
        class _FakeOrm:
            pass
        orm = _FakeOrm()
        orm.id = "abc"
        orm.username = "alice"
        orm.email = "alice@example.com"
        orm.hashed_password = "h$pw"
        orm.is_active = True
        orm.is_admin = False
        orm.api_quota = None
        orm.security_question = None
        orm.hashed_security_answer = None
        orm.active_session_id = None
        orm.active_session_ip = None
        orm.active_session_user_agent = None
        orm.active_session_started_at = datetime(2026, 6, 12, tzinfo=timezone.utc)
        orm.on_new_login_pref = "auto_kick"
        orm.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        orm.last_login = None

        dto = User.from_orm(orm)
        assert dto.active_session_started_at == "2026-06-12T00:00:00+00:00"  # nosec B101
        assert dto.created_at == "2026-01-01T00:00:00+00:00"  # nosec B101
        assert dto.last_login is None  # nosec B101


# ---------------------------------------------------------------------------
# UserManager CRUD (async, Fix #35)
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("user_manager")
class TestUserManagerCRUD:
    async def test_create_user_returns_dto(self, user_manager):
        u = await user_manager.create_user("alice", "alice@example.com", "hunter2")
        assert u.username == "alice"  # nosec B101
        assert u.email == "alice@example.com"  # nosec B101
        assert u.hashed_password != "hunter2"  # plaintext should NOT be stored  # nosec B101

    async def test_create_user_first_user_is_admin(self, user_manager):
        u = await user_manager.create_user("first", "first@example.com", "pw")
        assert u.is_admin is True  # nosec B101

    async def test_create_user_second_user_is_not_admin(self, user_manager):
        await user_manager.create_user("first", "first@example.com", "pw")
        u2 = await user_manager.create_user("second", "second@example.com", "pw")
        assert u2.is_admin is False  # nosec B101

    async def test_create_duplicate_user_raises(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        with pytest.raises(ValueError, match="already exists"):
            await user_manager.create_user("alice", "a2@example.com", "pw")

    async def test_get_user_returns_user_or_none(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        assert await user_manager.get_user("alice") is not None  # nosec B101
        assert await user_manager.get_user("nope") is None  # nosec B101

    async def test_update_password_succeeds(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "old_password")
        old_user = await user_manager.get_user("alice")
        old_hash = old_user.hashed_password
        assert await user_manager.update_password("alice", "new_password") is True  # nosec B101
        new_user = await user_manager.get_user("alice")
        assert new_user.hashed_password != old_hash  # nosec B101

    async def test_update_password_unknown_user_returns_false(self, user_manager):
        assert await user_manager.update_password("ghost", "pw") is False  # nosec B101

    async def test_persistence_across_manager_instances(self, user_manager, tmp_db):
        """Two UserManager instances against the same DB see the same users.
        (Pre-Fix-35 this was tested by writing to users.json + reloading
        with a new UserManager.)"""
        await user_manager.create_user("alice", "a@example.com", "pw")
        # A second UserManager against the same DB sees alice.
        mgr2 = UserManager()
        assert await mgr2.get_user("alice") is not None  # nosec B101


# ---------------------------------------------------------------------------
# UserManager authenticate
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("user_manager")
class TestUserManagerAuthenticate:
    async def test_authenticate_success(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "correct_pw")
        u = await user_manager.authenticate_user("alice", "correct_pw")
        assert u is not None  # nosec B101
        assert u.last_login is not None  # nosec B101

    async def test_authenticate_wrong_password(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "correct_pw")
        assert await user_manager.authenticate_user("alice", "wrong_pw") is None  # nosec B101

    async def test_authenticate_unknown_user(self, user_manager):
        assert await user_manager.authenticate_user("ghost", "anything") is None  # nosec B101

    async def test_authenticate_inactive_user(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        # The user is active by default; mark inactive via the repo.
        from core.database import UserRepository
        orm = await UserRepository.get_by_username("alice")
        from sqlalchemy import update as _u
        from core.database import db_manager
        from core.database import User as _UserModel
        async with db_manager.session_maker() as db:
            await db.execute(
                _u(_UserModel).where(_UserModel.id == orm.id).values(is_active=False)
            )
            await db.commit()
        assert await user_manager.authenticate_user("alice", "pw") is None  # nosec B101


# ---------------------------------------------------------------------------
# Security question
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("user_manager")
class TestUserManagerSecurityQuestion:
    async def test_set_then_has_security_question(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        assert await user_manager.set_security_question("alice", "First pet?", "rover") is True  # nosec B101
        assert await user_manager.has_security_question("alice") == "First pet?"  # nosec B101

    async def test_has_security_question_returns_none_for_no_question(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        assert await user_manager.has_security_question("alice") is None  # nosec B101

    async def test_has_security_question_does_not_leak_existence(self, user_manager):
        # Unknown user and existing user with no question should both
        # return None — callers can't distinguish "user doesn't exist"
        # from "user exists but has no question" (anti-enumeration).
        assert await user_manager.has_security_question("ghost") is None  # nosec B101

    async def test_verify_security_answer_correct(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        await user_manager.set_security_question("alice", "Pet?", "Rover")
        # The set path normalizes answer to lowercase, so case doesn't matter
        assert await user_manager.verify_security_answer("alice", "ROVER") is True  # nosec B101
        assert await user_manager.verify_security_answer("alice", "rover") is True  # nosec B101

    async def test_verify_security_answer_wrong(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        await user_manager.set_security_question("alice", "Pet?", "rover")
        assert await user_manager.verify_security_answer("alice", "fido") is False  # nosec B101

    async def test_verify_security_answer_no_question(self, user_manager):
        await user_manager.create_user("alice", "a@example.com", "pw")
        assert await user_manager.verify_security_answer("alice", "anything") is False  # nosec B101

    async def test_set_security_question_unknown_user(self, user_manager):
        assert await user_manager.set_security_question("ghost", "q?", "a") is False  # nosec B101


# ---------------------------------------------------------------------------
# Password hashing (sync, _hash_password + verify_password are sync)
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    """UserManager._hash_password and verify_password round-trip."""

    def test_hash_is_not_plaintext(self):
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        # The hash must NOT be the plaintext (any real hash function
        # has a prefix or transformation — even the test fake wraps
        # the password). When real bcrypt is wired in, this also
        # implies "longer than 72 bytes" but we don't assert that
        # here because the fake pwd_context doesn't match.
        assert h != "hunter2"  # nosec B101
        assert "hunter2" not in h or h.startswith(("h$", "plain:"))  # nosec B101

    def test_verify_correct_password(self):
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        assert mgr.verify_password("hunter2", h) is True  # nosec B101

    def test_verify_wrong_password(self):
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        assert mgr.verify_password("wrong", h) is False  # nosec B101

    def test_verify_garbage_hash_returns_false(self):
        mgr = UserManager()
        # Should not raise — verify_password catches exceptions
        assert mgr.verify_password("pw", "not-a-real-hash") is False  # nosec B101

    def test_verify_plain_prefix_legacy_hash(self):
        # Older installs have "plain:pw" hashes — the verify path
        # uses hmac.compare_digest for constant-time comparison.
        mgr = UserManager()
        assert mgr.verify_password("pw", "plain:pw") is True  # nosec B101
        assert mgr.verify_password("wrong", "plain:pw") is False  # nosec B101


# The JWT tests below require python-jose + passlib. If the
# environment doesn't have them, skip the entire block.
pytestmark_jwt = pytest.mark.skipif(
    not HAS_JWT,
    reason="python-jose / passlib not installed",
)


@pytestmark_jwt
class TestAccessToken:
    """create_access_token + verify_token round-trip.

    Fix #35: verify_token is now async."""
    pytestmark = pytest.mark.asyncio

    async def test_round_trip_preserves_claims(self):
        token = create_access_token({"sub": "user-123", "username": "alice"})
        data = await verify_token(token)
        assert data is not None  # nosec B101
        assert data.user_id == "user-123"  # nosec B101
        assert data.username == "alice"  # nosec B101

    async def test_custom_expiry_applied(self):
        # Issue with a 1-second expiry
        token = create_access_token(
            {"sub": "u", "username": "u"},
            expires_delta=timedelta(seconds=1),
        )
        # Should verify immediately
        assert await verify_token(token) is not None  # nosec B101

    async def test_garbage_token_returns_none(self):
        assert await verify_token("not.a.jwt") is None  # nosec B101

    async def test_empty_token_returns_none(self):
        assert await verify_token("") is None  # nosec B101

    async def test_tampered_signature_returns_none(self):
        token = create_access_token({"sub": "u", "username": "u"})
        # Flip the last character of the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert await verify_token(tampered) is None  # nosec B101


@pytestmark_jwt
class TestRefreshToken:
    """create_refresh_token + verify_refresh_token round-trip.

    Fix #35: ``verify_refresh_token`` stays sync — it does NOT do the
    single-session jti check (the access-token side does, via
    ``verify_token``). The refresh path applies the jti check in the
    route layer, not here."""
    pytestmark = pytest.mark.asyncio

    async def test_round_trip_preserves_claims(self):
        token = create_refresh_token({"sub": "u-1", "username": "alice"})
        data = verify_refresh_token(token)
        assert data is not None  # nosec B101
        assert data.user_id == "u-1"  # nosec B101
        assert data.username == "alice"  # nosec B101

    async def test_access_token_rejected_as_refresh(self):
        # An access token (no "type": "refresh" claim) must NOT
        # be accepted as a refresh token — type confusion attack.
        access = create_access_token({"sub": "u", "username": "u"})
        assert verify_refresh_token(access) is None  # nosec B101

    async def test_garbage_token_returns_none(self):
        assert verify_refresh_token("garbage") is None  # nosec B101


class TestCheckAdmin:
    """check_admin: trivial boolean check."""

    def test_admin_user_returns_true(self):
        u = User(id="x", username="a", email="e", is_admin=True)
        assert check_admin(u) is True  # nosec B101

    def test_regular_user_returns_false(self):
        u = User(id="x", username="a", email="e", is_admin=False)
        assert check_admin(u) is False  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
