"""
Tests for backend/modules/platform/unified_database.py — the
SQLite-backed CRUD store that replaces the scattered JSON files.

UnifiedDatabase is a thread-local SQLite singleton with CRUD for
conversations, settings, API keys, analytics events, and documents.
Every frontend list / save / delete hits one of these methods, so
regressions here show up as "my saved notes disappeared" reports.

The singleton pattern (UnifiedDatabase.__new__) is a pain to test
because the same instance is returned every time. We reset
`_instance = None` and re-init with a tmp_path fixture before each
test, and we monkey-patch the module-level `db` global so other
modules pick up the fresh instance.
"""

import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "platform"))

from modules.platform import unified_database
from modules.platform.unified_database import UnifiedDatabase, db, get_db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Reset the singleton, point it at a fresh tmp DB, return it.

    Every test gets a clean DB. We monkey-patch the module's `db`
    global so the convenience `get_db()` returns our fresh instance.
    """
    db_path = str(tmp_path / "test.db")
    # Reset singleton so __new__ will re-create
    UnifiedDatabase._instance = None
    # Also reset the imported `db` symbol
    import modules.platform.unified_database as ud_mod
    monkeypatch.setattr(ud_mod, "db", None)

    instance = UnifiedDatabase(db_path=db_path)
    monkeypatch.setattr(ud_mod, "db", instance)
    yield instance

    # Teardown: close connection
    try:
        if hasattr(instance._local, 'connection') and instance._local.connection:
            instance._local.connection.close()
    except Exception:
        pass
    UnifiedDatabase._instance = None


class TestSingletonBehavior:
    """The __new__ singleton contract."""

    def test_two_calls_return_same_instance(self, fresh_db):
        """UnifiedDatabase() called twice must return the same instance.

        With our fixture, _instance is set to `fresh_db`. A second
        call to UnifiedDatabase() should return the SAME object.
        """
        a = UnifiedDatabase()
        b = UnifiedDatabase()
        assert a is b
        assert a is fresh_db


class TestConversations:
    """save / get / list / delete / pin on the conversations table."""

    def test_save_and_get_conversation(self, fresh_db):
        ok = fresh_db.save_conversation({
            "id": "c1",
            "title": "Test convo",
            "category": "interview",
            "tags": ["python", "backend"],
            "messages": [{"role": "user", "text": "hi"}],
        })
        assert ok is True
        loaded = fresh_db.get_conversation("c1")
        assert loaded is not None
        assert loaded["id"] == "c1"
        assert loaded["title"] == "Test convo"
        # JSON columns are stored as strings, get_conversation returns raw row
        # so tags comes back as JSON string
        assert "python" in loaded["tags"]

    def test_get_missing_conversation(self, fresh_db):
        assert fresh_db.get_conversation("nonexistent") is None

    def test_list_conversations_returns_all(self, fresh_db):
        fresh_db.save_conversation({"id": "a", "title": "A"})
        fresh_db.save_conversation({"id": "b", "title": "B"})
        result = fresh_db.list_conversations()
        ids = {c["id"] for c in result}
        assert ids == {"a", "b"}

    def test_list_conversations_filter_by_category(self, fresh_db):
        fresh_db.save_conversation({"id": "a", "title": "A", "category": "interview"})
        fresh_db.save_conversation({"id": "b", "title": "B", "category": "general"})
        result = fresh_db.list_conversations(category="interview")
        assert len(result) == 1
        assert result[0]["id"] == "a"

    def test_list_conversations_pinned_first(self, fresh_db):
        fresh_db.save_conversation({"id": "old", "title": "Old"})
        fresh_db.save_conversation({"id": "new", "title": "New"})
        fresh_db.pin_conversation("old", True)
        result = fresh_db.list_conversations()
        # The pinned one should come first
        assert result[0]["id"] == "old"
        assert result[0]["pinned"] is True or result[0]["pinned"] == 1

    def test_list_conversations_excludes_archived_by_default(self, fresh_db):
        fresh_db.save_conversation({"id": "live", "title": "Live", "archived": False})
        fresh_db.save_conversation({"id": "old", "title": "Old", "archived": True})
        live = fresh_db.list_conversations(archived=False)
        assert {c["id"] for c in live} == {"live"}
        archived = fresh_db.list_conversations(archived=True)
        assert {c["id"] for c in archived} == {"old"}

    def test_delete_conversation(self, fresh_db):
        fresh_db.save_conversation({"id": "x", "title": "X"})
        assert fresh_db.delete_conversation("x") is True
        assert fresh_db.get_conversation("x") is None

    def test_delete_missing_conversation(self, fresh_db):
        assert fresh_db.delete_conversation("never-existed") is False

    def test_pin_conversation(self, fresh_db):
        fresh_db.save_conversation({"id": "p", "title": "P"})
        assert fresh_db.pin_conversation("p", True) is True
        loaded = fresh_db.get_conversation("p")
        assert loaded["pinned"] is True or loaded["pinned"] == 1

    def test_unpin_conversation(self, fresh_db):
        fresh_db.save_conversation({"id": "p", "title": "P", "pinned": True})
        fresh_db.pin_conversation("p", False)
        loaded = fresh_db.get_conversation("p")
        assert loaded["pinned"] is False or loaded["pinned"] == 0


class TestSettings:
    """set/get/delete + category filtering."""

    def test_set_and_get_string(self, fresh_db):
        fresh_db.set_setting("theme", "dark")
        assert fresh_db.get_setting("theme") == "dark"

    def test_set_and_get_int(self, fresh_db):
        fresh_db.set_setting("max_history", 100)
        assert fresh_db.get_setting("max_history") == 100

    def test_set_and_get_bool(self, fresh_db):
        fresh_db.set_setting("notifications_enabled", True)
        assert fresh_db.get_setting("notifications_enabled") is True

    def test_set_and_get_dict(self, fresh_db):
        fresh_db.set_setting("ui_config", {"font": "Inter", "size": 14})
        result = fresh_db.get_setting("ui_config")
        assert result == {"font": "Inter", "size": 14}

    def test_set_and_get_list(self, fresh_db):
        fresh_db.set_setting("allowed_models", ["gpt-4", "claude-3"])
        result = fresh_db.get_setting("allowed_models")
        assert result == ["gpt-4", "claude-3"]

    def test_get_missing_returns_default(self, fresh_db):
        assert fresh_db.get_setting("never-set", default="fallback") == "fallback"
        assert fresh_db.get_setting("never-set", default=None) is None

    def test_get_settings_by_category(self, fresh_db):
        fresh_db.set_setting("theme", "dark", category="ui")
        fresh_db.set_setting("font", "Inter", category="ui")
        fresh_db.set_setting("max_results", 50, category="search")
        ui = fresh_db.get_settings_by_category("ui")
        assert ui == {"theme": "dark", "font": "Inter"}

    def test_delete_setting(self, fresh_db):
        fresh_db.set_setting("k", "v")
        assert fresh_db.delete_setting("k") is True
        assert fresh_db.get_setting("k") is None

    def test_delete_missing_setting(self, fresh_db):
        assert fresh_db.delete_setting("never-existed") is False


class TestApiKeys:
    """save / get / list / delete on the api_keys table."""

    def test_save_and_get_api_key(self, fresh_db):
        fresh_db.save_api_key("openai", "sk-test-123")
        assert fresh_db.get_api_key("openai") == "sk-test-123"

    def test_list_api_keys(self, fresh_db):
        fresh_db.save_api_key("openai", "sk-openai")
        fresh_db.save_api_key("anthropic", "sk-anthropic")
        providers = fresh_db.list_api_keys()
        assert set(providers) == {"openai", "anthropic"}

    def test_get_missing_api_key(self, fresh_db):
        assert fresh_db.get_api_key("nonexistent") is None

    def test_delete_api_key(self, fresh_db):
        fresh_db.save_api_key("openai", "sk-test")
        assert fresh_db.delete_api_key("openai") is True
        assert fresh_db.get_api_key("openai") is None


class TestAnalyticsEvents:
    """record / get / summary on the analytics_events table."""

    def test_record_event(self, fresh_db):
        ok = fresh_db.record_analytics_event(
            event_type="conversation_started",
            event_data={"source": "web"},
        )
        assert ok is True

    def test_get_events_by_type(self, fresh_db):
        fresh_db.record_analytics_event("login", {"user": "alice"})
        fresh_db.record_analytics_event("login", {"user": "bob"})
        fresh_db.record_analytics_event("logout", {"user": "alice"})
        logins = fresh_db.get_analytics_events(event_type="login")
        assert len(logins) == 2

    def test_get_analytics_summary(self, fresh_db):
        fresh_db.record_analytics_event("page_view", {"path": "/"})
        fresh_db.record_analytics_event("page_view", {"path": "/about"})
        summary = fresh_db.get_analytics_summary(days=1)
        assert "total_events" in summary
        assert summary["total_events"] >= 2


class TestCacheHelpers:
    """cache_set / cache_get / cache_delete / cache_clear_expired."""

    def test_set_and_get(self, fresh_db):
        assert fresh_db.cache_set("k", "v") is True
        assert fresh_db.cache_get("k") == "v"

    def test_get_missing_returns_none(self, fresh_db):
        assert fresh_db.cache_get("never-set") is None

    def test_ttl_expiry(self):
        """Expired entries must return None on read.

        We use a separate DB instance so we don't pollute the
        shared singleton."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ttl_test.db")
            instance = UnifiedDatabase(db_path=path)
            instance.cache_set("k", "v", ttl_seconds=1)
            assert instance.cache_get("k") == "v"
            # Force expiry by manipulating the expires_at
            conn = instance._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cache SET expires_at = ? WHERE key = ?",
                ("2000-01-01T00:00:00", "k"),
            )
            conn.commit()
            assert instance.cache_get("k") is None

    def test_delete(self, fresh_db):
        fresh_db.cache_set("k", "v")
        assert fresh_db.cache_delete("k") is True
        assert fresh_db.cache_get("k") is None


class TestDocuments:
    """save / get / list on the documents table."""

    def test_save_and_get_document(self, fresh_db):
        ok = fresh_db.save_document({
            "id": "doc1",
            "filename": "resume.pdf",
            "type": "pdf",
            "content": "binary data",
        })
        assert ok is True
        loaded = fresh_db.get_document("doc1")
        assert loaded is not None
        assert loaded["filename"] == "resume.pdf"

    def test_list_documents(self, fresh_db):
        fresh_db.save_document({"id": "a", "filename": "a.pdf", "type": "pdf"})
        fresh_db.save_document({"id": "b", "filename": "b.pdf", "type": "pdf"})
        result = fresh_db.list_documents()
        assert len(result) == 2

    def test_list_processed_only(self, fresh_db):
        """`processed` is in the documents schema (unified_database.py CREATE TABLE)
        and save_document now writes it. `list_documents(processed_only=True)`
        should return only documents with processed=True."""
        fresh_db.save_document({
            "id": "raw", "filename": "raw.pdf", "type": "pdf", "processed": False
        })
        fresh_db.save_document({
            "id": "done", "filename": "done.pdf", "type": "pdf", "processed": True
        })
        processed = fresh_db.list_documents(processed_only=True)
        # Should return only the processed=True document
        assert len(processed) == 1
        assert processed[0]["id"] == "done"
        # SQLite returns 1/0 for boolean, so check truthiness
        assert processed[0]["processed"]


class TestConvenienceFunctions:
    """Module-level get_db() and the imported `db` symbol."""

    def test_get_db_returns_instance(self, fresh_db):
        # We monkey-patched `db` in the fixture, so get_db should
        # return our fresh instance.
        result = get_db()
        assert result is fresh_db


class TestValueCasting:
    """_cast_value: the round-trip helper that restores Python types."""

    def test_cast_string(self, fresh_db):
        assert fresh_db._cast_value("hello", "str") == "hello"

    def test_cast_int(self, fresh_db):
        assert fresh_db._cast_value("42", "int") == 42

    def test_cast_float(self, fresh_db):
        assert fresh_db._cast_value("3.14", "float") == 3.14

    def test_cast_bool_true(self, fresh_db):
        assert fresh_db._cast_value("true", "bool") is True

    def test_cast_bool_false(self, fresh_db):
        assert fresh_db._cast_value("false", "bool") is False

    def test_cast_dict(self, fresh_db):
        assert fresh_db._cast_value('{"a": 1}', "dict") == {"a": 1}

    def test_cast_list(self, fresh_db):
        assert fresh_db._cast_value("[1, 2, 3]", "list") == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
