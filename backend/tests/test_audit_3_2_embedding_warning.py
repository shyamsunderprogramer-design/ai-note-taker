"""
Regression test for audit item 3.2 followup — startup warning when
EMBEDDING_ENABLED=false but cognitive features are available.

Background: `render.yaml` sets `EMBEDDING_ENABLED: "false"` and
`CLASSIFIER_ENABLED: "false"` by default to save ~420MB RAM on the
free tier. The cognitive_graph module uses embeddings for semantic
search; when `EMBEDDING_AVAILABLE` is False at runtime,
`cognitive_graph._init_semantic_search()` short-circuits to
`legacy_keyword_search()` (a Cypher CONTAINS-based fallback). Without
a startup warning, free-tier users see silently degraded search
results with no signal that an env var would fix it.

The fix extracts the warning logic into `_warn_on_optional_ml_disabled()`
(in `core/main.py`) so it can be unit-tested directly without spinning
up the full app. Two warning paths are tested:

1. **Embedding path**: warns when `EMBEDDING_ENABLED=false` AND
   `COGNITIVE_GRAPH_AVAILABLE=true` (the exact case the audit called out).
2. **Classifier path**: warns when `CLASSIFIER_ENABLED=false` AND
   `modules.ai.smart_classifier` is importable.

The test mocks `config.EMBEDDING_ENABLED` / `config.CLASSIFIER_ENABLED`
and the module-level `COGNITIVE_GRAPH_AVAILABLE` flag in `core.main`.
"""

import logging
import os
import sys
from unittest.mock import patch

import pytest

# Add backend/ to sys.path so `from core.main import ...` resolves.
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

# Import the symbols under test. The module has heavy side effects on
# import (loads routes, registers middleware, etc.) so we isolate the
# test by importing the helpers first.
from core.main import _warn_on_optional_ml_disabled, _smart_classifier_importable


class TestWarnOnOptionalMLDisabled:
    """Startup warning fires under the right conditions and stays silent
    under the wrong ones."""

    def test_warns_when_embedding_disabled_and_cognitive_graph_available(self, caplog):
        """The exact audit case: EMBEDDING_ENABLED=false, COGNITIVE_GRAPH_AVAILABLE=true."""
        with patch("core.config.EMBEDDING_ENABLED", False), \
             patch("core.config.CLASSIFIER_ENABLED", True), \
             patch("core.main.COGNITIVE_GRAPH_AVAILABLE", True), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "EMBEDDING_ENABLED=false" in warning_text, (
            f"Expected embedding warning in logs, got: {warning_text!r}"
        )
        assert "cognitive graph is available" in warning_text
        assert "legacy_keyword_search" in warning_text
        # The warning should point the user at the env var to flip.
        assert "EMBEDDING_ENABLED=true" in warning_text

    def test_silent_when_embedding_enabled(self, caplog):
        """If EMBEDDING_ENABLED=true, no embedding warning should fire."""
        with patch("core.config.EMBEDDING_ENABLED", True), \
             patch("core.config.CLASSIFIER_ENABLED", True), \
             patch("core.main.COGNITIVE_GRAPH_AVAILABLE", True), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "EMBEDDING_ENABLED=false" not in warning_text, (
            f"Should NOT warn when EMBEDDING_ENABLED=true. Got: {warning_text!r}"
        )

    def test_silent_when_cognitive_graph_unavailable(self, caplog):
        """If the consumer (cognitive_graph) isn't available, no point warning."""
        with patch("core.config.EMBEDDING_ENABLED", False), \
             patch("core.config.CLASSIFIER_ENABLED", True), \
             patch("core.main.COGNITIVE_GRAPH_AVAILABLE", False), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "EMBEDDING_ENABLED=false" not in warning_text, (
            f"Should NOT warn when cognitive graph is unavailable. Got: {warning_text!r}"
        )

    def test_silent_in_cloud_mode(self, caplog):
        """Cloud deploys disable these by design (free-tier cost savings).
        Warning on every cloud boot would be noise."""
        with patch("core.config.EMBEDDING_ENABLED", False), \
             patch("core.config.CLASSIFIER_ENABLED", False), \
             patch("core.main.COGNITIVE_GRAPH_AVAILABLE", True), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=True)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "EMBEDDING_ENABLED=false" not in warning_text, (
            f"Should NOT warn in CLOUD_MODE. Got: {warning_text!r}"
        )
        assert "CLASSIFIER_ENABLED=false" not in warning_text, (
            f"Should NOT warn in CLOUD_MODE. Got: {warning_text!r}"
        )

    def test_warns_classifier_when_disabled_and_module_importable(self, caplog):
        """Mirror test for the classifier branch."""
        # The smart_classifier module IS importable in this env (it's
        # in the project tree under modules/ai/smart_classifier.py).
        assert _smart_classifier_importable(), (
            "Test prerequisite failed: smart_classifier should be importable "
            "in this env to exercise the warning path."
        )

        with patch("core.config.EMBEDDING_ENABLED", True), \
             patch("core.config.CLASSIFIER_ENABLED", False), \
             patch("core.main.COGNITIVE_GRAPH_AVAILABLE", False), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "CLASSIFIER_ENABLED=false" in warning_text, (
            f"Expected classifier warning in logs, got: {warning_text!r}"
        )
        assert "smart classifier module is importable" in warning_text
        assert "CLASSIFIER_ENABLED=true" in warning_text

    def test_silent_classifier_when_enabled(self, caplog):
        """If CLASSIFIER_ENABLED=true, no classifier warning."""
        with patch("core.config.EMBEDDING_ENABLED", True), \
             patch("core.config.CLASSIFIER_ENABLED", True), \
             caplog.at_level(logging.WARNING, logger="main"):
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "CLASSIFIER_ENABLED=false" not in warning_text

    def test_silent_when_config_not_importable(self, caplog):
        """If `core.config` can't be imported, bail silently rather than
        crashing startup."""
        # Simulate the import failure by patching `importlib.import_module`
        # to raise ImportError for both `core.config` and `config`.
        # That's the only call path the function uses, so the function
        # should return without logging anything.
        import importlib
        real_import_module = importlib.import_module

        def fake_import_module(name, *args, **kwargs):
            if name in ("config", "core.config"):
                raise ImportError(f"simulated: {name}")
            return real_import_module(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=fake_import_module), \
             caplog.at_level(logging.WARNING, logger="main"):
            # Should NOT raise; should silently return.
            _warn_on_optional_ml_disabled(CLOUD_MODE=False)

        # If we got here without raising, the test passes.
        warning_text = "\n".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
        assert "EMBEDDING_ENABLED=false" not in warning_text


class TestSmartClassifierImportable:
    """The `_smart_classifier_importable` probe used by the warning."""

    def test_returns_true_when_module_exists(self):
        # smart_classifier.py is in modules/ai/ of this project, so the
        # find_spec probe should succeed.
        assert _smart_classifier_importable() is True

    def test_returns_false_for_nonexistent_module(self):
        # Use a clearly-fake module name to ensure the probe returns
        # False (not None) on miss. Defensive: callers may use `is True`.
        with patch.dict(sys.modules, {}), \
             patch("importlib.util.find_spec", return_value=None):
            assert _smart_classifier_importable() is False

    def test_returns_false_on_import_error(self):
        # If find_spec itself raises (very unlikely but possible if
        # importlib is broken), the helper should return False, not
        # propagate. This is a defensive test against a hard-to-trigger
        # but real failure mode.
        with patch("importlib.util.find_spec", side_effect=RuntimeError("boom")):
            assert _smart_classifier_importable() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
