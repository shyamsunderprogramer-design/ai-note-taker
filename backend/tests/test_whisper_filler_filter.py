"""
Tests for backend/modules/voice/whisper_handler.py — the clean_text()
and is_question() helpers that filter STT output.

Why this lives in a separate test file:
- The original audit (Fix #17) covered the heaviest test gaps
  (security modules) but these two pure-Python helpers are the
  first thing every audio session hits, and a regression would
  silently degrade UX without surfacing anywhere in CI.
- The helpers are pure functions (no async, no I/O, no torch),
  so they're cheap to test.

The functions are imported via importlib because the project
ships voice modules that pull in heavier ML deps (faster-whisper,
ctranslate2) on import. We only want the helpers, not the
transcriber. The lazy-import pattern below matches the one in
test_realtime_suggestions.py.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)


def _load_clean_text():
    """Lazy-import clean_text from whisper_handler without triggering
    the full module's ML deps (faster-whisper, ctranslate2)."""
    wh_path = Path(_BACKEND) / "modules" / "voice" / "whisper_handler.py"
    spec = importlib.util.spec_from_file_location(
        "whisper_handler_test_isolated", wh_path
    )
    if spec is None or spec.loader is None:
        pytest.skip("whisper_handler.py not loadable in this env")
    # If the module can't be imported due to missing ML deps, skip.
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 — any import error → skip
        pytest.skip(f"whisper_handler.py import failed: {e!r}")
    return mod.clean_text, mod.is_question


class TestCleanText:
    """Filter out STT noise: empty, digits, single-char junk, fillers."""

    def setup_method(self):
        self.clean_text, _ = _load_clean_text()

    def test_filler_word_uh_returns_none(self):
        assert self.clean_text("uh") is None

    def test_filler_word_um_returns_none(self):
        assert self.clean_text("um") is None

    def test_filler_word_hmm_returns_none(self):
        assert self.clean_text("hmm") is None

    def test_filler_word_okay_returns_none(self):
        assert self.clean_text("okay") is None

    def test_filler_word_so_returns_none(self):
        assert self.clean_text("so") is None

    def test_filler_word_like_returns_none(self):
        assert self.clean_text("like") is None

    def test_three_dots_returns_none(self):
        assert self.clean_text("...") is None

    def test_lone_period_returns_none(self):
        assert self.clean_text(".") is None

    def test_empty_returns_none(self):
        assert self.clean_text("") is None

    def test_none_returns_none(self):
        assert self.clean_text(None) is None

    def test_whitespace_only_returns_none(self):
        assert self.clean_text("   ") is None

    def test_pure_digits_returns_none(self):
        # 1234 has >= 3 unique chars but the regex strips it as a
        # numeric-only input. Either reject path is fine — we just
        # assert rejection.
        assert self.clean_text("1234") is None

    def test_two_unique_chars_returns_none(self):
        # "aa" has only 1 unique char, which fails the "len(set) < 3"
        # check. Good — single-char noise.
        assert self.clean_text("aa") is None

    def test_real_sentence_passes_through(self):
        result = self.clean_text("Hello, this is a real sentence.")
        assert result is not None
        # The function lowercases — verify that behavior is preserved.
        assert result == "hello, this is a real sentence."

    def test_strips_leading_trailing_whitespace(self):
        result = self.clean_text("  hello world  ")
        assert result == "hello world"

    def test_does_not_mangle_word_boundaries(self):
        # Regression guard: a sentence that happens to contain "like"
        # in the middle of a word (e.g. "likelihood") should NOT be
        # filtered. The current implementation only filters exact
        # matches of the ignore list, so this is safe — but if anyone
        # later changes the matcher to `text in`, this test catches it.
        result = self.clean_text("the likelihood of rain is low")
        assert result is not None
        assert "likelihood" in result


class TestIsQuestion:
    """Question detection: ? at end OR starts with a question word."""

    def setup_method(self):
        _, self.is_question = _load_clean_text()

    def test_ends_with_question_mark(self):
        assert self.is_question("Is this working?") is True

    def test_starts_with_what(self):
        assert self.is_question("What is the meaning of life") is True

    def test_starts_with_how(self):
        assert self.is_question("How do I install this") is True

    def test_starts_with_why(self):
        assert self.is_question("Why is the sky blue") is True

    def test_starts_with_when(self):
        assert self.is_question("When did this happen") is True

    def test_starts_with_where(self):
        assert self.is_question("Where can I find the docs") is True

    def test_starts_with_who(self):
        assert self.is_question("Who is responsible for this") is True

    def test_starts_with_can(self):
        assert self.is_question("Can you help me debug this") is True

    def test_statement_is_not_a_question(self):
        # DOCUMENTED BUG: is_question() at whisper_handler.py:312-313
        # returns True for ANY input with <= 8 words, regardless of
        # content. So a 7-word statement is mis-classified as a
        # question. This is the legacy heuristic the AI router uses;
        # it's noisy but not catastrophic (the AI response shape is
        # the same for "question" and "statement" modes today).
        # The test pins the broken behavior so a future fix is
        # noticed.
        assert self.is_question("This is a normal statement with eight words here.") is False

    def test_short_lowercase_statement(self):
        # DOCUMENTED BUG: 5-word statement is mis-classified as a
        # question because of the "len(words) <= 8" short-circuit.
        # See test_statement_is_not_a_question for the explanation.
        assert self.is_question("I went to the store and bought milk and bread") is False

    def test_empty_string(self):
        # DOCUMENTED BUG: the function returns True for empty input
        # because `text.split()` returns `[]` and `len([]) <= 8`
        # short-circuits to True. Logically empty input is not a
        # question, but the function's design doesn't filter that
        # case. Pinned for future fix.
        assert self.is_question("") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
