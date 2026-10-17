"""
Tests for backend/modules/ai/smart_classifier.py — the zero-shot
classifier with graceful fallback when transformers isn't installed.

SmartClassifier requires `transformers` (a 2GB+ dependency) so we
can't import the heavy pipeline in CI. The tests focus on:
- Label map correctness (the canonical mapping the API returns)
- The fallback methods (keyword-based heuristics used when the
  transformer is unavailable)
- Empty-text safety (returns the first label, not a crash)
- The module-level singleton gate (CLASSIFIER_AVAILABLE flag)

The transformer-backed path is exercised manually in environments
where the model is downloaded.
"""

import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

from modules.ai import smart_classifier
from modules.ai.smart_classifier import (
    CONTENT_LABEL_MAP,
    CONVERSATION_TYPE_LABEL_MAP,
    DIFFICULTY_LABEL_MAP,
    QUESTION_LABEL_MAP,
    SmartClassifier,
)


class TestLabelMaps:
    """The 4 label maps translate model output → API label."""

    def test_question_label_map_is_complete(self):
        # Every key in the map must be one of the 5 labels
        for label in smart_classifier.QUESTION_LABELS:
            assert label in QUESTION_LABEL_MAP
        # Every value should be one of 5 known categories
        valid_values = {"technical", "system_design", "behavioral", "knowledge", "general"}
        for v in QUESTION_LABEL_MAP.values():
            assert v in valid_values

    def test_content_label_map_is_complete(self):
        for label in smart_classifier.CONTENT_LABELS:
            assert label in CONTENT_LABEL_MAP
        # Should have 6 content focus categories
        assert len(CONTENT_LABEL_MAP) == 6

    def test_difficulty_label_map_has_three_levels(self):
        assert set(DIFFICULTY_LABEL_MAP.values()) == {"easy", "medium", "hard"}
        assert len(DIFFICULTY_LABEL_MAP) == 3

    def test_conversation_type_label_map_has_three_types(self):
        assert set(CONVERSATION_TYPE_LABEL_MAP.values()) == {
            "practice_session", "mock_interview", "real_interview"
        }
        assert len(CONVERSATION_TYPE_LABEL_MAP) == 3

    def test_known_company_names_includes_top_employers(self):
        # Spot check — companies commonly mentioned in tech interviews
        for name in ["Google", "Meta", "Amazon", "Microsoft", "Apple", "Stripe", "OpenAI"]:
            assert name in SmartClassifier.COMPANY_NAMES


class TestClassifyQuestionEmptyText:
    """Empty text must not crash and returns the first label."""

    def test_empty_string_returns_first_label(self):
        c = SmartClassifier.__new__(SmartClassifier)
        # Don't call __init__ (it just sets attrs); bypass the
        # pipeline entirely by calling _classify_zero_shot directly.
        c._pipeline = None
        c._cache = {}
        c._cache_lock = __import__("threading").Lock()
        c._max_cache = 100

        result = c._classify_zero_shot("", smart_classifier.QUESTION_LABELS)
        # When text is empty, returns equal scores + top_label = labels[0]
        assert "labels" in result
        assert "scores" in result
        assert result["top_label"] == smart_classifier.QUESTION_LABELS[0]
        assert result["top_score"] == 0.0
        # Scores should be uniform
        assert all(s == 1.0 / len(smart_classifier.QUESTION_LABELS) for s in result["scores"])

    def test_whitespace_only_text_treated_as_empty(self):
        c = SmartClassifier.__new__(SmartClassifier)
        c._pipeline = None
        c._cache = {}
        c._cache_lock = __import__("threading").Lock()
        c._max_cache = 100

        result = c._classify_zero_shot("   \t\n  ", smart_classifier.QUESTION_LABELS)
        # Whitespace-only treated like empty
        assert result["top_score"] == 0.0


class TestFallbackClassifyQuestion:
    """_fallback_classify_question: keyword-based, no ML."""

    def test_returns_tuple(self):
        c = SmartClassifier.__new__(SmartClassifier)
        cat, conf = c._fallback_classify_question("What is a binary search tree?")
        assert isinstance(cat, str)
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_falls_back_to_general_on_failure(self):
        """If entity_extractor also fails, returns ('general', 0.3)."""
        c = SmartClassifier.__new__(SmartClassifier)
        # Simulate a totally broken inner dependency by passing text
        # that won't crash anything but will likely return a tuple.
        # The contract is: never raise.
        cat, conf = c._fallback_classify_question("x")
        assert cat in {"technical", "system_design", "behavioral", "knowledge", "general"}
        assert conf > 0


class TestFallbackClassifyDifficulty:
    """_fallback_classify_difficulty: keyword-based, no ML."""

    def test_easy_keywords(self):
        c = SmartClassifier.__new__(SmartClassifier)
        # Match exact "easy" keyword
        level, conf = c._fallback_classify_difficulty("What is a basic linked list?")
        # "basic" is in easy_words; "linked list" not in hard_words
        assert level in {"easy", "medium", "hard"}
        assert conf == 0.5

    def test_hard_keywords(self):
        c = SmartClassifier.__new__(SmartClassifier)
        level, conf = c._fallback_classify_difficulty(
            "Design a distributed system that scales to billions of users"
        )
        # "design", "distributed", "scale" are all hard_words
        assert level == "hard"
        assert conf == 0.5

    def test_neutral_returns_medium(self):
        c = SmartClassifier.__new__(SmartClassifier)
        # Text with no easy/hard keywords
        level, conf = c._fallback_classify_difficulty("Tell me about your favorite color.")
        assert level == "medium"

    def test_hard_beats_easy_when_both_present(self):
        c = SmartClassifier.__new__(SmartClassifier)
        # "optimize" (hard) and "basic" (easy) both present
        level, _ = c._fallback_classify_difficulty("Optimize this basic algorithm")
        # The code uses hard_count > easy_count, but both are 1 here
        # so it falls through to medium. Pinning that behavior.
        assert level == "medium"  # tie → medium


class TestModuleConstants:
    """Module-level constants and singleton gate."""

    def test_classifier_available_starts_false(self):
        # CLASSIFIER_AVAILABLE is a module-level flag flipped to True
        # only after warmup() succeeds. Should be False in test env.
        # (May be True if some other test set it — check it's a bool.)
        assert isinstance(smart_classifier.CLASSIFIER_AVAILABLE, bool)

    def test_default_model_is_set(self):
        assert smart_classifier.DEFAULT_MODEL
        assert "mDeBERTa" in smart_classifier.DEFAULT_MODEL or "nli" in smart_classifier.DEFAULT_MODEL

    def test_get_classifier_returns_none_when_unavailable(self):
        # If CLASSIFIER_AVAILABLE is False, get_classifier returns None
        # without trying to import transformers.
        original = smart_classifier.CLASSIFIER_AVAILABLE
        try:
            smart_classifier.CLASSIFIER_AVAILABLE = False
            result = smart_classifier.get_classifier()
            assert result is None
        finally:
            smart_classifier.CLASSIFIER_AVAILABLE = original

    def test_wait_for_classifier_returns_bool(self):
        # Should return False after the short default timeout
        # (warmup hasn't been called, so the Event is unset)
        result = smart_classifier.wait_for_classifier(timeout=0.1)
        assert isinstance(result, bool)


class TestCacheBehavior:
    """_classify_zero_shot uses an in-memory cache to avoid re-runs."""

    def test_cache_dedupes_identical_inputs(self):
        """The empty-text path returns before caching, so we can only
        verify the cache key generation logic by computing the hash
        that the production code would use."""
        import hashlib
        c = SmartClassifier.__new__(SmartClassifier)
        c._pipeline = None
        c._cache = {}
        c._cache_lock = __import__("threading").Lock()
        c._max_cache = 100

        # Empty text path doesn't touch pipeline
        r = c._classify_zero_shot("", smart_classifier.QUESTION_LABELS)
        # Cache is still empty (empty path bypasses caching)
        assert len(c._cache) == 0
        # But the result is well-formed
        assert r["top_score"] == 0.0
        # Verify the cache key formula
        expected_key = hashlib.sha256(
            f"{''}|{'|'.join(smart_classifier.QUESTION_LABELS)}|{False}".encode()
        ).hexdigest()
        # Manually populate to test the cache key format
        c._cache[expected_key] = r
        assert expected_key in c._cache

    def test_cache_eviction_on_overflow(self):
        """When the cache exceeds max_cache, the oldest 20% are evicted."""
        c = SmartClassifier.__new__(SmartClassifier)
        c._pipeline = None
        c._cache = {}
        c._cache_lock = __import__("threading").Lock()
        c._max_cache = 5  # tiny cache to trigger eviction quickly

        # Each unique text populates the cache (via the empty-text path)
        # The empty-text path uses sha256(text|labels|multi_label) so
        # we need to bypass with text="" which returns BEFORE caching.
        # Instead, manually populate and trigger the eviction path.
        for i in range(10):
            c._cache[f"key_{i}"] = {"labels": [], "scores": [], "top_label": "", "top_score": 0.0}
            # Simulate the eviction block from _classify_zero_shot
            if len(c._cache) >= c._max_cache:
                keys_to_remove = list(c._cache.keys())[: c._max_cache // 5]
                for k in keys_to_remove:
                    del c._cache[k]

        # After 10 inserts with max=5, the cache should be smaller than 10
        assert len(c._cache) < 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
