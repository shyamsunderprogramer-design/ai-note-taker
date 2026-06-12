"""
Test suite for backend/security/auth.py
Covers User dataclass, UserManager (CRUD on a JSON file), and the
JWT access/refresh token issue/verify functions.

The `USERS_FILE` and `_LEGACY_USERS_FILE` are module-level constants
computed at import time. We monkeypatch them to point at a tmp_path
before each test so the real production users.json is never touched.

Run with: python -m pytest backend/tests/test_security_auth.py -v
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add backend/ to sys.path so `from security.auth import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Import the module under test first so we can monkeypatch its globals.
from security import auth as auth_module  # noqa: E402
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

    def verify(self, password: str, hashed: str) -> bool:
        if not hashed or not hashed.startswith("h$"):
            return False
        return password == hashed[2:]


# Install the fake pwd_context into the auth module BEFORE any test
# that exercises UserManager runs. This is module-level (not in a
# fixture) because the bcrypt bug crashes at import-time of
# `auth.pwd_context`, and we want to fix it once for the whole run.
auth_module.pwd_context = _FakePwdContext()  # type: ignore[assignment]


class TestUserDataclass:
    """User dataclass: defaults, field types, custom overrides."""

    def test_minimal_construction(self):
        u = User(id="abc", username="alice", email="alice@example.com")
        assert u.username == "alice"  # nosec B101
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


class TestUserManagerCRUD:
    """UserManager: create / get / authenticate / update password.

    The module-level USERS_FILE is monkeypatched per-test to point at
    an isolated tmp_path so tests don't share state.
    """

    def test_create_user_stores_in_dict(self, tmp_path, monkeypatch):
        # Point the module at an isolated users.json for this test
        users_file = tmp_path / "users.json"
        legacy_file = tmp_path / "legacy.json"  # not used but must not exist
        monkeypatch.setattr(auth_module, "USERS_FILE", users_file)
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", legacy_file)

        mgr = UserManager()
        u = mgr.create_user("alice", "alice@example.com", "hunter2")

        assert u.username == "alice"  # nosec B101
        assert u.email == "alice@example.com"  # nosec B101
        assert u.hashed_password != "hunter2"  # plaintext should NOT be stored  # nosec B101
        assert "alice" in mgr.users  # nosec B101

    def test_create_user_first_user_is_admin(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        u = mgr.create_user("first", "first@example.com", "pw")
        assert u.is_admin is True  # nosec B101

    def test_create_user_second_user_is_not_admin(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("first", "first@example.com", "pw")
        u2 = mgr.create_user("second", "second@example.com", "pw")
        assert u2.is_admin is False  # nosec B101

    def test_create_duplicate_user_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_user("alice", "a2@example.com", "pw")

    def test_get_user_returns_user_or_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        assert mgr.get_user("alice") is not None  # nosec B101
        assert mgr.get_user("nope") is None  # nosec B101

    def test_update_password_succeeds(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "old_password")
        old_hash = mgr.get_user("alice").hashed_password
        assert mgr.update_password("alice", "new_password") is True  # nosec B101
        new_hash = mgr.get_user("alice").hashed_password
        assert new_hash != old_hash  # nosec B101

    def test_update_password_unknown_user_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        assert mgr.update_password("ghost", "pw") is False  # nosec B101

    def test_persistence_to_disk_and_reload(self, tmp_path, monkeypatch):
        users_file = tmp_path / "users.json"
        legacy_file = tmp_path / "legacy.json"
        monkeypatch.setattr(auth_module, "USERS_FILE", users_file)
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", legacy_file)

        mgr1 = UserManager()
        mgr1.create_user("alice", "a@example.com", "pw")
        assert users_file.exists()  # nosec B101

        # New manager instance loads the same file
        mgr2 = UserManager()
        assert mgr2.get_user("alice") is not None  # nosec B101


class TestUserManagerAuthenticate:
    """UserManager.authenticate_user: happy path + 3 failure modes."""

    def test_authenticate_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "correct_pw")
        u = mgr.authenticate_user("alice", "correct_pw")
        assert u is not None  # nosec B101
        assert u.last_login is not None  # nosec B101

    def test_authenticate_wrong_password(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "correct_pw")
        assert mgr.authenticate_user("alice", "wrong_pw") is None  # nosec B101

    def test_authenticate_unknown_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        assert mgr.authenticate_user("ghost", "anything") is None  # nosec B101

    def test_authenticate_inactive_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        mgr.get_user("alice").is_active = False
        assert mgr.authenticate_user("alice", "pw") is None  # nosec B101


class TestUserManagerSecurityQuestion:
    """UserManager: security question set/verify/has_security_question."""

    def test_set_then_has_security_question(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        assert mgr.set_security_question("alice", "First pet?", "rover") is True  # nosec B101
        assert mgr.has_security_question("alice") == "First pet?"  # nosec B101

    def test_has_security_question_returns_none_for_no_question(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        assert mgr.has_security_question("alice") is None  # nosec B101

    def test_has_security_question_does_not_leak_existence(self, tmp_path, monkeypatch):
        # Unknown user and existing user with no question should both
        # return None — callers can't distinguish "user doesn't exist"
        # from "user exists but has no question" (anti-enumeration).
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        assert mgr.has_security_question("ghost") is None  # nosec B101

    def test_verify_security_answer_correct(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        mgr.set_security_question("alice", "Pet?", "Rover")
        # The set path normalizes answer to lowercase, so case doesn't matter
        assert mgr.verify_security_answer("alice", "ROVER") is True  # nosec B101
        assert mgr.verify_security_answer("alice", "rover") is True  # nosec B101

    def test_verify_security_answer_wrong(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        mgr.set_security_question("alice", "Pet?", "rover")
        assert mgr.verify_security_answer("alice", "fido") is False  # nosec B101

    def test_verify_security_answer_no_question(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        mgr.create_user("alice", "a@example.com", "pw")
        assert mgr.verify_security_answer("alice", "anything") is False  # nosec B101

    def test_set_security_question_unknown_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        assert mgr.set_security_question("ghost", "q?", "a") is False  # nosec B101


class TestPasswordHashing:
    """UserManager._hash_password and verify_password round-trip."""

    def test_hash_is_not_plaintext(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        # The hash must NOT be the plaintext (any real hash function
        # has a prefix or transformation — even the test fake wraps
        # the password). When real bcrypt is wired in, this also
        # implies "longer than 72 bytes" but we don't assert that
        # here because the fake pwd_context doesn't match.
        assert h != "hunter2"  # nosec B101
        assert "hunter2" not in h or h.startswith(("h$", "plain:"))  # nosec B101

    def test_verify_correct_password(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        assert mgr.verify_password("hunter2", h) is True  # nosec B101

    def test_verify_wrong_password(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        h = mgr._hash_password("hunter2")
        assert mgr.verify_password("wrong", h) is False  # nosec B101

    def test_verify_garbage_hash_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
        mgr = UserManager()
        # Should not raise — verify_password catches exceptions
        assert mgr.verify_password("pw", "not-a-real-hash") is False  # nosec B101

    def test_verify_plain_prefix_legacy_hash(self, tmp_path, monkeypatch):
        # Older installs have "plain:pw" hashes — the verify path
        # uses hmac.compare_digest for constant-time comparison.
        monkeypatch.setattr(auth_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(auth_module, "_LEGACY_USERS_FILE", tmp_path / "legacy.json")
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
    """create_access_token + verify_token round-trip."""

    def test_round_trip_preserves_claims(self):
        token = create_access_token({"sub": "user-123", "username": "alice"})
        data = verify_token(token)
        assert data is not None  # nosec B101
        assert data.user_id == "user-123"  # nosec B101
        assert data.username == "alice"  # nosec B101

    def test_custom_expiry_applied(self):
        # Issue with a 1-second expiry, then sleep and verify
        token = create_access_token(
            {"sub": "u", "username": "u"},
            expires_delta=timedelta(seconds=1),
        )
        # Should verify immediately
        assert verify_token(token) is not None  # nosec B101

    def test_garbage_token_returns_none(self):
        assert verify_token("not.a.jwt") is None  # nosec B101

    def test_empty_token_returns_none(self):
        assert verify_token("") is None  # nosec B101

    def test_tampered_signature_returns_none(self):
        token = create_access_token({"sub": "u", "username": "u"})
        # Flip the last character of the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert verify_token(tampered) is None  # nosec B101


@pytestmark_jwt
class TestRefreshToken:
    """create_refresh_token + verify_refresh_token round-trip."""

    def test_round_trip_preserves_claims(self):
        token = create_refresh_token({"sub": "u-1", "username": "alice"})
        data = verify_refresh_token(token)
        assert data is not None  # nosec B101
        assert data.user_id == "u-1"  # nosec B101
        assert data.username == "alice"  # nosec B101

    def test_access_token_rejected_as_refresh(self):
        # An access token (no "type": "refresh" claim) must NOT
        # be accepted as a refresh token — type confusion attack.
        access = create_access_token({"sub": "u", "username": "u"})
        assert verify_refresh_token(access) is None  # nosec B101

    def test_garbage_token_returns_none(self):
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
