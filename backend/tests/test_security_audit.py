"""
Test suite for backend/security/audit.py
Covers the AuditEvent dataclass, the _sanitize_for_log helper,
and the JSONL fallback path of log_audit_event / get_audit_log /
get_audit_stats.

The audit module writes to a module-level AUDIT_LOG_DIR / AUDIT_LOG_FILE
that defaults to "data/audit_logs/audit.jsonl" relative to CWD. We
monkeypatch them to point at a tmp_path per-test so the real audit
log is never touched.

The async database-write path is intentionally not tested here — it
would require the full SQLAlchemy stack and a live database, which
contradicts the test tier in Fix #17's scope (security + small
helpers, no DB).

Run with: python -m pytest backend/tests/test_security_audit.py -v
"""

import json
import logging
import os
import sys

import pytest

# Add backend/ to sys.path so `from security.audit import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from security import audit as audit_module  # noqa: E402
from security.audit import (  # noqa: E402
    AuditEvent,
    _sanitize_for_log,
    log_audit_event,
    get_audit_log,
    get_audit_stats,
)


@pytest.fixture
def isolated_audit_dir(tmp_path, monkeypatch):
    """Point the module's AUDIT_LOG_DIR at a tmp_path so each test
    gets a clean, isolated JSONL file. Returns the tmp_path."""
    log_dir = tmp_path / "audit_logs"
    log_file = log_dir / "audit.jsonl"
    monkeypatch.setattr(audit_module, "AUDIT_LOG_DIR", str(log_dir))
    monkeypatch.setattr(audit_module, "AUDIT_LOG_FILE", str(log_file))
    return tmp_path


class TestSanitizeForLog:
    """_sanitize_for_log: remove newlines/tabs to prevent log injection."""

    def test_strips_newline(self):
        assert _sanitize_for_log("line1\nline2") == "line1\\nline2"  # nosec B101

    def test_strips_carriage_return(self):
        assert _sanitize_for_log("line1\rline2") == "line1\\rline2"  # nosec B101

    def test_strips_tab(self):
        assert _sanitize_for_log("col1\tcol2") == "col1\\tcol2"  # nosec B101

    def test_preserves_normal_text(self):
        assert _sanitize_for_log("hello world") == "hello world"  # nosec B101

    def test_coerces_non_string(self):
        assert _sanitize_for_log(42) == "42"  # nosec B101
        assert _sanitize_for_log(None) == "None"  # nosec B101

    def test_combined_injection_attempt(self):
        # The classic log-injection attack:
        #   attacker logs in with username = "alice\n[ERROR] admin logged out"
        # The \n would normally add a fake log line. _sanitize_for_log
        # escapes it to \n literal text.
        evil = "alice\n[ERROR] admin logged out"
        sanitized = _sanitize_for_log(evil)
        assert "\n" not in sanitized  # nosec B101
        assert "\\n" in sanitized  # nosec B101


class TestAuditEventDataclass:
    """AuditEvent: defaults, serialization."""

    def test_minimal_construction(self):
        e = AuditEvent(
            timestamp="2026-06-05T00:00:00Z",
            event_type="auth_login",
            actor="alice",
            action="login",
            resource="",
        )
        assert e.actor == "alice"  # nosec B101
        assert e.success is True  # nosec B101
        assert e.details == {}  # nosec B101
        assert e.ip_address == ""  # nosec B101
        assert e.user_agent == ""  # nosec B101

    def test_to_dict_via_asdict(self):
        e = AuditEvent(
            timestamp="2026-06-05T00:00:00Z",
            event_type="auth_login",
            actor="alice",
            action="login",
            resource="",
            details={"ip": "1.2.3.4"},
        )
        d = json.dumps(e.__dict__)  # dataclass instance is JSON-serializable
        assert "auth_login" in d  # nosec B101


class TestLogAuditEvent:
    """log_audit_event: writes a JSONL record to the file."""

    def test_writes_jsonl_entry(self, isolated_audit_dir):
        log_audit_event(
            event_type="auth_login",
            actor="alice",
            action="login",
        )
        # The module-level AUDIT_LOG_FILE was patched to point at tmp
        log_file = audit_module.AUDIT_LOG_FILE
        assert os.path.exists(log_file)  # nosec B101
        with open(log_file) as f:
            line = f.readline().strip()
        entry = json.loads(line)
        assert entry["event_type"] == "auth_login"  # nosec B101
        assert entry["actor"] == "alice"  # nosec B101
        assert entry["action"] == "login"  # nosec B101
        assert entry["success"] is True  # nosec B101
        # Timestamp is UTC ISO format with 'Z' suffix
        assert entry["timestamp"].endswith("Z")  # nosec B101

    def test_failure_event_marked(self, isolated_audit_dir):
        log_audit_event(
            event_type="auth_failure",
            actor="alice",
            action="login",
            success=False,
        )
        with open(audit_module.AUDIT_LOG_FILE) as f:
            entry = json.loads(f.readline().strip())
        assert entry["success"] is False  # nosec B101

    def test_details_dict_persisted(self, isolated_audit_dir):
        log_audit_event(
            event_type="data_create",
            actor="alice",
            action="create_note",
            resource="note/123",
            details={"size": 1024, "tags": ["work", "urgent"]},
        )
        with open(audit_module.AUDIT_LOG_FILE) as f:
            entry = json.loads(f.readline().strip())
        assert entry["details"]["size"] == 1024  # nosec B101
        assert "work" in entry["details"]["tags"]  # nosec B101

    def test_appends_multiple_entries(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        log_audit_event("auth_logout", "alice", "logout")
        log_audit_event("data_create", "alice", "create_note")
        with open(audit_module.AUDIT_LOG_FILE) as f:
            lines = [l for l in f.readlines() if l.strip()]
        assert len(lines) == 3  # nosec B101
        assert json.loads(lines[0])["event_type"] == "auth_login"  # nosec B101
        assert json.loads(lines[1])["event_type"] == "auth_logout"  # nosec B101
        assert json.loads(lines[2])["event_type"] == "data_create"  # nosec B101

    def test_sanitizes_log_output(self, isolated_audit_dir, caplog):
        # The Python logger output must be sanitized — no raw \n
        # from a malicious actor name.
        caplog.set_level(logging.WARNING)
        evil_actor = "alice\n[FAKE LOG ENTRY] admin logged in"
        log_audit_event(
            event_type="auth_failure",
            actor=evil_actor,
            action="login",
            success=False,
        )
        # Find the log record
        audit_records = [r for r in caplog.records if "FAKE LOG ENTRY" in r.getMessage()]
        # The literal "FAKE LOG ENTRY" should appear (sanitized) but
        # on a single log line — never as a separate record
        for record in audit_records:
            assert "\n" not in record.getMessage()  # nosec B101


class TestGetAuditLog:
    """get_audit_log: read + filter from JSONL."""

    def test_returns_empty_when_no_file(self, isolated_audit_dir):
        # File doesn't exist yet — should return [] not raise
        assert get_audit_log() == []  # nosec B101

    def test_returns_all_entries(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        log_audit_event("auth_logout", "alice", "logout")
        entries = get_audit_log()
        assert len(entries) == 2  # nosec B101

    def test_filter_by_event_type(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        log_audit_event("auth_logout", "alice", "logout")
        log_audit_event("auth_login", "bob", "login")
        entries = get_audit_log(event_type="auth_login")
        assert len(entries) == 2  # nosec B101
        assert all(e["event_type"] == "auth_login" for e in entries)  # nosec B101

    def test_filter_by_actor(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        log_audit_event("auth_login", "bob", "login")
        entries = get_audit_log(actor="alice")
        assert len(entries) == 1  # nosec B101
        assert entries[0]["actor"] == "alice"  # nosec B101

    def test_limit_truncates(self, isolated_audit_dir):
        for i in range(10):
            log_audit_event("data_create", f"user_{i}", "create")
        entries = get_audit_log(limit=3)
        assert len(entries) == 3  # nosec B101

    def test_skips_malformed_lines(self, isolated_audit_dir):
        # Manually write a file with one good and one bad line.
        # The fixture patches AUDIT_LOG_FILE; ensure the parent dir
        # exists before writing.
        log_file = audit_module.AUDIT_LOG_FILE
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "w") as f:
            f.write(json.dumps({"event_type": "good", "actor": "a", "action": "x"}) + "\n")
            f.write("not-valid-json\n")
            f.write(json.dumps({"event_type": "good2", "actor": "b", "action": "y"}) + "\n")
        entries = get_audit_log()
        assert len(entries) == 2  # nosec B101
        assert entries[0]["event_type"] == "good"  # nosec B101
        assert entries[1]["event_type"] == "good2"  # nosec B101


class TestGetAuditStats:
    """get_audit_stats: aggregate counts from the JSONL."""

    def test_empty_file_returns_zero_total(self, isolated_audit_dir):
        stats = get_audit_stats()
        assert stats["total_events"] == 0  # nosec B101

    def test_counts_total_events(self, isolated_audit_dir):
        for _ in range(5):
            log_audit_event("auth_login", "alice", "login")
        stats = get_audit_stats()
        assert stats["total_events"] == 5  # nosec B101

    def test_counts_by_event_type(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        log_audit_event("auth_login", "bob", "login")
        log_audit_event("auth_logout", "alice", "logout")
        stats = get_audit_stats()
        assert stats["event_types"]["auth_login"] == 2  # nosec B101
        assert stats["event_types"]["auth_logout"] == 1  # nosec B101

    def test_counts_failures(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login", success=True)
        log_audit_event("auth_failure", "alice", "login", success=False)
        log_audit_event("auth_failure", "bob", "login", success=False)
        stats = get_audit_stats()
        assert stats["failures"] == 2  # nosec B101

    def test_includes_last_event_timestamp(self, isolated_audit_dir):
        log_audit_event("auth_login", "alice", "login")
        stats = get_audit_stats()
        assert stats["last_event"] is not None  # nosec B101
        assert stats["last_event"].endswith("Z")  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
