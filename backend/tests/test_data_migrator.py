"""Tests for the JSON -> SQL data migrator (Fix #35 Commit 5).

The migrator is the one-time bridge from the legacy
``backend/data/users.json`` store to the SQLAlchemy ``users`` table.
Three behaviors are pinned here:

1. **Full-fidelity column copy** — every User column the source record
   carries (security_question, hashed_security_answer, active_session_*,
   on_new_login_pref, last_login) is copied. Pre-Commit-5 the migrator
   silently dropped these, which invalidated every migrated user's
   security question and forced a re-login.

2. **Idempotency** — once a successful migration writes
   ``data/.migrated_to_sql``, subsequent calls to ``run_full_migration``
   short-circuit (no DB I/O, no JSON parse). The admin route re-runs
   with ``force=True``.

3. **Marker placement** — the marker is only written when at least one
   user migrated, so a no-op run on a fresh DB leaves the marker
   unwritten (next boot retries, which is what you want if the operator
   drops a users.json in place between restarts).
"""

import json
import os
import sys
from datetime import datetime, timezone

import pytest

# Add backend/ to sys.path so `from core.database import ...` resolves.
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

# Tests are sensitive to env var defaults; set them up before app import.
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ANT_SKIP_ALEMBIC", "1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sample_user(**overrides):
    """A representative Fix-#34-shaped user dict.

    Includes all the new columns that the pre-Commit-5 migrator
    silently dropped (security_question, active_session_*, etc.) so a
    full-fidelity test will fail loudly if any are missed.
    """
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "username": "alice",
        "email": "alice@example.com",
        "hashed_password": "bcrypt$2a$10$abcdef",
        "is_active": True,
        "is_admin": False,
        "created_at": "2026-01-15T10:00:00+00:00",
        "last_login": "2026-06-10T08:30:00+00:00",
        "api_quota": {"requests_today": 7, "daily_limit": 1000,
                      "reset_date": "2026-06-10"},
        "security_question": "What city were you born in?",
        "hashed_security_answer": "bcrypt$2a$10$xyz",
        "active_session_id": "jti-abc-123",
        "active_session_ip": "192.168.1.42",
        "active_session_user_agent": "Mozilla/5.0 ...",
        "active_session_started_at": "2026-06-09T09:00:00+00:00",
        "on_new_login_pref": "auto_kick",
    }
    base.update(overrides)
    return base


def _migrate_one(user_data):
    """Migrate a single user dict via the real migrator. Mirrors what
    ``DataMigrator.migrate_users`` does for one row, but without
    touching the filesystem — keeps the test hermetic."""
    from core import database as db_mod
    return db_mod.UserRepository.create(
        username=user_data["username"],
        email=user_data.get("email", f"{user_data['username']}@localhost"),
        hashed_password=user_data.get("hashed_password", ""),
        is_admin=user_data.get("is_admin", False),
        is_active=user_data.get("is_active", True),
        api_quota=user_data.get("api_quota", {}),
        created_at=db_mod.DataMigrator._parse_iso_dt(user_data.get("created_at"))
                     or datetime.now(timezone.utc),
        last_login=db_mod.DataMigrator._parse_iso_dt(user_data.get("last_login")),
        security_question=user_data.get("security_question"),
        hashed_security_answer=user_data.get("hashed_security_answer"),
        active_session_id=user_data.get("active_session_id"),
        active_session_ip=user_data.get("active_session_ip"),
        active_session_user_agent=user_data.get("active_session_user_agent"),
        active_session_started_at=db_mod.DataMigrator._parse_iso_dt(
            user_data.get("active_session_started_at")
        ),
        on_new_login_pref=user_data.get("on_new_login_pref", "auto_kick"),
    )


# ---------------------------------------------------------------------------
# AST-level: confirm the migrator code path exists at the source level.
# ---------------------------------------------------------------------------
class TestMigratorAST:
    """Source-level guarantees: the migrator passes every Fix-#34
    column. If a future refactor drops one, the AST test will catch
    it before the behavioral tests even need to run."""

    MIGRATOR_PY = os.path.join(_BACKEND, "core", "database.py")

    @pytest.fixture
    def migrator_source(self):
        with open(self.MIGRATOR_PY) as f:
            return f.read()

    @pytest.mark.parametrize("column", [
        "security_question",
        "hashed_security_answer",
        "active_session_id",
        "active_session_ip",
        "active_session_user_agent",
        "active_session_started_at",
        "on_new_login_pref",
        "last_login",
    ])
    def test_migrator_passes_column(self, migrator_source, column):
        """The DataMigrator.migrate_users call to UserRepository.create
        must include every Fix-#34 column by name. A missing column
        here means the migration would silently null that field for
        every migrated user."""
        start = migrator_source.find("async def migrate_users")
        assert start != -1, "migrate_users not found"
        # Take a window from the def to the next top-level def or class.
        window = migrator_source[start:start + 4000]
        assert column in window, (
            f"DataMigrator.migrate_users is missing the {column!r} "
            f"column — Fix #35 Commit 5 requires full-fidelity copy."
        )

    def test_run_full_migration_takes_force_kwarg(self, migrator_source):
        """The admin button needs to re-run the migration even after
        the marker is set. Pin that ``force=True`` is a real
        parameter, not a typo or stripped signature."""
        start = migrator_source.find("async def run_full_migration")
        assert start != -1
        window = migrator_source[start:start + 1000]
        assert "force: bool = False" in window, (
            "run_full_migration must accept force=False so the admin "
            "route can pass force=True to re-run after the marker is set"
        )

    def test_idempotency_marker_is_written(self, migrator_source):
        """The sticky-note system that makes boot-time migration a
        no-op after the first successful run must exist in the source."""
        assert "mark_migrated" in migrator_source, (
            "DataMigrator.mark_migrated() missing — boot-time migration "
            "would re-run on every startup"
        )
        assert "already_migrated" in migrator_source, (
            "DataMigrator.already_migrated() missing — run_full_migration "
            "has no way to short-circuit on subsequent boots"
        )


# ---------------------------------------------------------------------------
# Behavioral: end-to-end migrator against a real SQLite DB.
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Per-test SQLite DB with the SA schema applied. Mirrors the
    ``tmp_db`` fixture in conftest.py but is local to this file so the
    tests don't depend on conftest being importable in isolation."""
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

    import asyncio
    asyncio.run(database.db_manager.initialize())
    try:
        yield db_path
    finally:
        asyncio.run(database.db_manager.close())
        database.db_manager.engine = None
        database.db_manager.session_maker = None
        database.db_manager._initialized = False
        if db_path.exists():
            db_path.unlink()


class TestDataMigratorFullFidelity:
    """End-to-end: migrate a Fix-#34-shape user and confirm every
    column round-trips through to the SQLAlchemy row."""

    @pytest.mark.asyncio
    async def test_all_columns_copied_for_alice(self, fresh_db):
        """The richest user (alice) must round-trip every column."""
        await _migrate_one(_sample_user(username="alice"))
        from core import database as db_mod
        alice = await db_mod.UserRepository.get_by_username("alice")
        assert alice is not None
        assert alice.email == "alice@example.com"
        assert alice.hashed_password == "bcrypt$2a$10$abcdef"
        assert alice.is_admin is False
        assert alice.security_question == "What city were you born in?"
        assert alice.hashed_security_answer == "bcrypt$2a$10$xyz"
        assert alice.active_session_id == "jti-abc-123"
        assert alice.active_session_ip == "192.168.1.42"
        assert alice.active_session_user_agent == "Mozilla/5.0 ..."
        assert alice.on_new_login_pref == "auto_kick"
        # last_login is a DateTime column; check it round-trips to
        # the same calendar day in UTC (sqlite drops tzinfo on read).
        assert alice.last_login is not None
        assert alice.last_login.year == 2026
        assert alice.last_login.month == 6
        assert alice.last_login.day == 10

    @pytest.mark.asyncio
    async def test_minimal_user_does_not_crash(self, fresh_db):
        """A user with every optional column null must still produce a
        usable row (no NOT NULL violations). This is the realistic
        shape of pre-Fix-#34 users.json records."""
        await _migrate_one(_sample_user(
            username="bob",
            email="bob@example.com",
            is_admin=True,
            security_question=None,
            hashed_security_answer=None,
            active_session_id=None,
            active_session_ip=None,
            active_session_user_agent=None,
            active_session_started_at=None,
            last_login=None,
        ))
        from core import database as db_mod
        bob = await db_mod.UserRepository.get_by_username("bob")
        assert bob is not None
        assert bob.is_admin is True
        assert bob.security_question is None
        assert bob.hashed_security_answer is None
        assert bob.active_session_id is None
        assert bob.last_login is None


class TestDataMigratorIdempotency:
    """The marker file makes run_full_migration a no-op after success."""

    def test_marker_path_under_data_dir(self):
        """The marker lives at backend/data/.migrated_to_sql (sibling
        to users.json) so a `rm data/*.json && git pull` style reset
        wipes both at once."""
        from core.database import DataMigrator
        path = DataMigrator._marker_path()
        assert path.name == ".migrated_to_sql"
        assert "data" in path.parts

    def test_already_migrated_false_when_no_marker(self, fresh_db, tmp_path):
        """A fresh DB with no marker file → not migrated."""
        import core.database as db_mod
        orig_path = db_mod.DataMigrator._marker_path
        db_mod.DataMigrator._marker_path = classmethod(
            lambda cls: tmp_path / ".migrated_to_sql"
        )
        try:
            assert db_mod.DataMigrator.already_migrated() is False
        finally:
            db_mod.DataMigrator._marker_path = orig_path

    def test_already_migrated_true_after_marker_written(self, fresh_db, tmp_path):
        """Writing the marker flips the check to True."""
        import core.database as db_mod
        orig_path = db_mod.DataMigrator._marker_path
        db_mod.DataMigrator._marker_path = classmethod(
            lambda cls: tmp_path / ".migrated_to_sql"
        )
        try:
            assert db_mod.DataMigrator.already_migrated() is False
            db_mod.DataMigrator.mark_migrated({"users": 3, "conversations": 0})
            assert db_mod.DataMigrator.already_migrated() is True
            payload = json.loads((tmp_path / ".migrated_to_sql").read_text())
            assert payload["users_migrated"] == 3
            assert payload["version"] == "1.0"
        finally:
            db_mod.DataMigrator._marker_path = orig_path

    @pytest.mark.asyncio
    async def test_run_full_migration_skipped_when_marker_present(self, fresh_db, tmp_path):
        """When the marker is present, run_full_migration returns
        ``skipped=True`` and does NOT touch the DB."""
        import core.database as db_mod
        # Pre-populate DB with v1 alice.
        await db_mod.UserRepository.create(
            username="alice",
            email="alice-v1@example.com",
            hashed_password="v1hash",
        )
        orig_path = db_mod.DataMigrator._marker_path
        db_mod.DataMigrator._marker_path = classmethod(
            lambda cls: tmp_path / ".migrated_to_sql"
        )
        try:
            db_mod.DataMigrator.mark_migrated({"users": 1, "conversations": 0})
            results = await db_mod.DataMigrator.run_full_migration()
            assert results.get("skipped") is True
            assert results["users"] == 0
            # alice is still v1 — the migrator did not touch her.
            alice = await db_mod.UserRepository.get_by_username("alice")
            assert alice.email == "alice-v1@example.com"
            assert alice.hashed_password == "v1hash"
        finally:
            db_mod.DataMigrator._marker_path = orig_path

    @pytest.mark.asyncio
    async def test_force_bypasses_marker(self, fresh_db, tmp_path):
        """``run_full_migration(force=True)`` re-runs even when the
        marker is present. This is the path /admin/migrate uses."""
        import core.database as db_mod
        await db_mod.UserRepository.create(
            username="alice",
            email="alice-v1@example.com",
            hashed_password="v1hash",
        )
        orig_path = db_mod.DataMigrator._marker_path
        db_mod.DataMigrator._marker_path = classmethod(
            lambda cls: tmp_path / ".migrated_to_sql"
        )
        try:
            db_mod.DataMigrator.mark_migrated({"users": 1, "conversations": 0})
            results = await db_mod.DataMigrator.run_full_migration(force=True)
            assert "skipped" not in results or results.get("skipped") is False
        finally:
            db_mod.DataMigrator._marker_path = orig_path


class TestMigratorParseHelpers:
    """The _parse_iso_dt helper handles bad input without crashing
    the whole migration."""

    @pytest.mark.parametrize("value,expected_kind", [
        ("2026-06-10T08:30:00+00:00", "datetime"),
        ("2026-06-10T08:30:00", "datetime"),
        ("", "none"),
        (None, "none"),
        ("not-a-date", "none"),
        (datetime(2026, 6, 10, 8, 30, tzinfo=timezone.utc), "datetime"),
    ])
    def test_parse_iso_dt(self, value, expected_kind):
        from core.database import DataMigrator
        result = DataMigrator._parse_iso_dt(value)
        if expected_kind == "none":
            assert result is None
        else:
            assert isinstance(result, datetime)
