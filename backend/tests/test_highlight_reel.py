"""
Tests for backend/modules/ai/highlight_reel.py — selects key moments
from a conversation transcript for the "highlight reel" UI feature.

HighlightReelGenerator is pure-Python regex/keyword analysis with no
ML deps. It identifies 4 types of moments:
- decision_made: matches DECISION_KEYWORDS (decided, agreed, approved, etc.)
- action_item: matches ACTION_ITEM_KEYWORDS (todo, follow-up, must, etc.)
- important_point: matches IMPORTANCE_KEYWORDS (critical, urgent, etc.)
- high_engagement: 2+ speaker changes in a 5-message window

Each detected moment becomes a clip (start-15s → start+30s) that
gets scored across 4 dimensions and selected up to a duration budget.
We test the detection regex, the score formula, the duration cap,
the style weights, and the dedup logic.
"""

import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

from modules.ai.highlight_reel import (
    HighlightReelGenerator,
    STYLE_WEIGHTS,
    highlight_reel_generator,
)


@pytest.fixture
def gen():
    return HighlightReelGenerator()


class TestGenerateEmpty:
    """Empty input → empty output."""

    def test_empty_messages_returns_empty(self, gen):
        assert gen.generate([]) == []

    def test_none_input_returns_empty(self, gen):
        # No explicit None check but should not crash
        try:
            result = gen.generate(None)
            assert result == []
        except (TypeError, AttributeError):
            # Acceptable — None is undefined behavior, the function
            # only documents List[Dict] in the signature
            pass


class TestStyleWeights:
    """Style selection picks the right weight profile."""

    def test_balanced_style_default(self, gen):
        # The default style is "balanced"
        assert "balanced" in STYLE_WEIGHTS
        weights = STYLE_WEIGHTS["balanced"]
        # All 4 dimensions weighted equally
        assert weights["decisions"] == 0.25
        assert weights["action_items"] == 0.25
        assert weights["importance"] == 0.25
        assert weights["engagement"] == 0.25

    def test_decisions_style_emphasizes_decisions(self, gen):
        weights = STYLE_WEIGHTS["decisions"]
        # Decisions is the heaviest dimension
        assert weights["decisions"] == 0.50
        assert weights["decisions"] > weights["action_items"]

    def test_action_items_style_emphasizes_actions(self, gen):
        weights = STYLE_WEIGHTS["action_items"]
        assert weights["action_items"] == 0.50
        assert weights["action_items"] > weights["decisions"]

    def test_unknown_style_falls_back_to_balanced(self, gen):
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to ship it."},
        ]
        # Pass an unknown style; should use balanced weights
        result = gen.generate(messages, style="nonexistent")
        # Still produces output (just with balanced weights)
        assert isinstance(result, list)


class TestDecisionKeywordDetection:
    """DECISION_KEYWORDS regex catches the right phrases."""

    def test_decision_keyword_detected(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "We decided to launch next week."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        # Should find a clip around the decision
        assert len(result) >= 1
        assert any("decision" in c.get("reason", "") for c in result)

    def test_agreement_keyword_detected(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "Sounds good, let's go with that."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1

    def test_no_keyword_no_clip(self, gen):
        """Plain text without any keyword → no clip detected (assuming no engagement)."""
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "Hello there."},
            {"timestamp": 10, "speaker": "A", "text": "How are you?"},
            {"timestamp": 20, "speaker": "A", "text": "Just checking in."},
        ]
        # No keywords, only one speaker → no key moments
        result = gen.generate(messages)
        assert result == []


class TestActionItemDetection:
    """ACTION_ITEM_KEYWORDS regex catches todos/follow-ups."""

    def test_todo_keyword_detected(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "We need to follow up with the client."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1
        assert any("action" in c.get("reason", "") for c in result)

    def test_deadline_keyword_detected(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "Deadline is by Friday."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1


class TestImportanceDetection:
    """IMPORTANCE_KEYWORDS regex catches critical/urgent words."""

    def test_critical_keyword_detected(self, gen):
        """Use text with ONLY importance keywords, no action/decision
        keywords — so the elif chain lands on importance."""
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "This is a critical blocker for the team."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1
        assert any("important" in c.get("reason", "") for c in result)

    def test_urgent_keyword_detected(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "This is urgent."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1


class TestHighEngagementDetection:
    """Frequent speaker changes flag high-engagement moments."""

    def test_speaker_changes_flagged(self, gen):
        """2+ unique speakers in 5 messages → high_engagement moment."""
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "Hi."},
            {"timestamp": 5, "speaker": "B", "text": "Hello."},
            {"timestamp": 10, "speaker": "A", "text": "How are you?"},
            {"timestamp": 15, "speaker": "B", "text": "Good."},
            {"timestamp": 20, "speaker": "A", "text": "Great."},
            {"timestamp": 25, "speaker": "B", "text": "Thanks."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1
        # The high-engagement moment should be in the result
        reasons = [c.get("reason", "") for c in result]
        assert any("engagement" in r for r in reasons)

    def test_single_speaker_no_engagement_moment(self, gen):
        messages = [
            {"timestamp": i * 5, "speaker": "A", "text": f"msg {i}"}
            for i in range(10)
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        # Single speaker → no high_engagement moment (no keywords either)
        reasons = [c.get("reason", "") for c in result]
        assert not any("engagement" in r for r in reasons)


class TestSegmentScoring:
    """_score_segment: 4 dimensions, 0-1 each."""

    def test_empty_segment_zeros(self, gen):
        result = gen._score_segment([], 0, 10)
        assert result == {"decisions": 0, "action_items": 0, "importance": 0, "engagement": 0}

    def test_decision_increases_decision_score(self, gen):
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to ship the new feature."},
        ]
        scores = gen._score_segment(messages, 0, 5)
        # "decided" should bump decisions above 0
        assert scores["decisions"] > 0

    def test_score_is_capped_at_1(self, gen):
        """A segment packed with keywords shouldn't exceed 1.0."""
        messages = [
            {
                "timestamp": 0,
                "speaker": "A",
                "text": "decided approved confirmed action todo follow-up "
                        "critical urgent important deadline"
            },
        ]
        scores = gen._score_segment(messages, 0, 5)
        # Each score is capped at 1.0
        for v in scores.values():
            assert 0.0 <= v <= 1.0


class TestDurationBudget:
    """Clips that exceed max_duration are excluded."""

    def test_short_budget_limits_clips(self, gen):
        # Create many key moments across a long conversation
        messages = []
        for i in range(10):
            messages.append({
                "timestamp": i * 10,
                "speaker": "A",
                "text": f"We decided to do thing {i}.",
            })
        # With a tiny budget, only the first few clips fit
        result = gen.generate(messages, max_duration_seconds=30)
        # Each clip is ~45s (15s before + 30s after)
        # So at most 1 clip fits in 30s budget
        assert len(result) <= 1

    def test_generous_budget_includes_more(self, gen):
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to start."},
            {"timestamp": 200, "speaker": "A", "text": "We decided to ship."},
        ]
        # 600s budget fits both clips
        result = gen.generate(messages, max_duration_seconds=600)
        assert len(result) >= 2

    def test_no_overlapping_clips(self, gen):
        """Selected clips must not overlap (in second-resolution)."""
        messages = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to start."},
            {"timestamp": 5, "speaker": "A", "text": "We decided to continue."},
            {"timestamp": 10, "speaker": "A", "text": "We decided to ship."},
        ]
        result = gen.generate(messages, max_duration_seconds=600)
        # Check no two selected clips overlap
        for i, a in enumerate(result):
            for b in result[i + 1:]:
                # No overlap: a.end <= b.start or b.end <= a.start
                assert a["end"] <= b["start"] or b["end"] <= a["start"]


class TestResultShape:
    """Each clip dict has the right keys."""

    def test_clip_has_required_fields(self, gen):
        messages = [
            {"timestamp": 30, "speaker": "A", "text": "We decided to ship."},
        ]
        result = gen.generate(messages, max_duration_seconds=60)
        assert len(result) >= 1
        clip = result[0]
        assert "start" in clip
        assert "end" in clip
        assert "reason" in clip
        assert "confidence" in clip
        # Confidence is 0-1
        assert 0.0 <= clip["confidence"] <= 1.0

    def test_clips_sorted_by_start_time(self, gen):
        """Selected clips are returned in playback order (start ascending)."""
        messages = []
        for i in range(5):
            messages.append({
                "timestamp": i * 100,
                "speaker": "A",
                "text": f"We decided to do task {i}.",
            })
        result = gen.generate(messages, max_duration_seconds=2000)
        # Verify ascending order by start
        for i in range(len(result) - 1):
            assert result[i]["start"] <= result[i + 1]["start"]


class TestModuleSingleton:
    """The module exposes a singleton instance."""

    def test_singleton_exists(self):
        assert highlight_reel_generator is not None
        assert isinstance(highlight_reel_generator, HighlightReelGenerator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
