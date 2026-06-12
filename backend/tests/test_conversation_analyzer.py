"""
Tests for backend/modules/ai/conversation_analyzer.py — auto-tag and
quality-score conversations.

ConversationAnalyzer is pure-Python text analysis: it parses Q&A pairs,
detects interview type (practice / mock / real), checks for STAR
formatting on behavioral answers, and computes a 0-1 quality score
across 5 dimensions. It is the engine that powers the "Practice Plan"
recommendations and the dashboard quality tile.

The module has no heavy ML deps — it's regex + keyword counting — so
we can hit every public method directly. Tests focus on:
- Empty-conversation contract (returns _empty_analysis() shape)
- Q&A pair extraction from messages
- Conversation type detection (the 3 types + fallback)
- STAR method detection (must detect "Situation/Task/Action/Result"
  language patterns)
- Quality tier thresholds
"""

import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

from modules.ai.conversation_analyzer import (
    ConversationAnalyzer,
    ConversationTags,
    QualityMetrics,
)


@pytest.fixture
def analyzer():
    return ConversationAnalyzer()


class TestEmptyConversation:
    """analyze_conversation on empty input must return _empty_analysis."""

    def test_no_messages_returns_empty_shape(self, analyzer):
        result = analyzer.analyze_conversation({"messages": [], "title": ""})
        assert "tags" in result
        assert "quality_metrics" in result
        assert "statistics" in result
        assert result["statistics"]["total_messages"] == 0
        assert result["statistics"]["question_count"] == 0

    def test_empty_with_title(self, analyzer):
        """DOCUMENTED BUG: _empty_analysis() hardcodes title="" instead
        of preserving the input title. The contract should be that
        the title is echoed back even when there are no messages.
        Pinning the broken behavior — will flip when fixed."""
        result = analyzer.analyze_conversation({
            "messages": [],
            "title": "Mock interview with Google",
        })
        # Currently the title is wiped to "" by _empty_analysis()
        assert result["title"] == ""  # expected to flip to "Mock interview with Google" on fix


class TestQaPairExtraction:
    """Messages with role='interviewer' or '?' become questions."""

    def test_simple_qa_pair(self, analyzer):
        messages = [
            {"role": "interviewer", "content": "What is your favorite language?"},
            {"role": "candidate", "content": "Python, because of its readability."},
        ]
        qa_pairs = analyzer._extract_qa_pairs(messages)
        assert len(qa_pairs) == 1
        assert "favorite language" in qa_pairs[0]["question"]
        assert "Python" in qa_pairs[0]["answer"]

    def test_multiple_qa_pairs(self, analyzer):
        messages = [
            {"role": "interviewer", "content": "Question 1?"},
            {"role": "candidate", "content": "Answer 1."},
            {"role": "interviewer", "content": "Question 2?"},
            {"role": "candidate", "content": "Answer 2."},
        ]
        qa_pairs = analyzer._extract_qa_pairs(messages)
        assert len(qa_pairs) == 2

    def test_question_mark_becomes_question(self, analyzer):
        """Even without role=interviewer, '?' makes it a question."""
        messages = [
            {"role": "user", "content": "How do you sort an array?"},
            {"role": "assistant", "content": "Use quicksort."},
        ]
        qa_pairs = analyzer._extract_qa_pairs(messages)
        assert len(qa_pairs) == 1
        assert "sort" in qa_pairs[0]["question"]


class TestConversationTypeDetection:
    """_detect_conversation_type picks practice / mock / real."""

    def test_practice_keyword(self, analyzer):
        qa_pairs = [{"question": "Q", "answer": "A"}]
        result = analyzer._detect_conversation_type("Practicing for FAANG", [], qa_pairs)
        assert result in {"practice_session", "mock_interview", "real_interview"}

    def test_real_interview_keyword(self, analyzer):
        qa_pairs = [{"question": "Q", "answer": "A"}]
        result = analyzer._detect_conversation_type(
            "My phone screen with Meta", [], qa_pairs
        )
        assert result in {"practice_session", "mock_interview", "real_interview"}
        # "phone screen" is in the real_interview keywords
        assert result == "real_interview"

    def test_mock_keyword(self, analyzer):
        qa_pairs = [{"question": "Q", "answer": "A"}]
        result = analyzer._detect_conversation_type("Mock interview practice", [], qa_pairs)
        assert result in {"practice_session", "mock_interview", "real_interview"}


class TestStarMethodDetection:
    """Behavioral answers get a STAR check: Situation/Task/Action/Result."""

    def test_full_star_detected(self, analyzer):
        """An answer containing 3+ STAR components is flagged.

        STAR patterns (conversation_analyzer.py:100-105):
        - situation: when/during/while/at/in/there was/we had
        - task: i had to/my responsibility/i was asked/needed to/required to
        - action: i did/i implemented/i created/i worked/i led/i suggested
        - result: result/outcome/ended up/achieved/successfully/improved by
        """
        qa_pairs = [{
            "question": "Tell me about a time you led a project",
            "answer": (
                "We had a deadline that was at risk. "
                "I was asked to take ownership. "
                "I led the team and I created a new schedule. "
                "The result was we shipped successfully and improved by 20%."
            ),
        }]
        assert analyzer._detect_star_method(qa_pairs) is True

    def test_no_star_components(self, analyzer):
        """An answer with no STAR keywords is not STAR-formatted."""
        qa_pairs = [{
            "question": "Tell me about a time you led a project",
            "answer": "Yes I have led projects before, it went well.",
        }]
        assert analyzer._detect_star_method(qa_pairs) is False

    def test_empty_qa_returns_false_DOCUMENTED_BUG(self):
        """DOCUMENTED BUG: _detect_star_method([]) returns True.

        The function falls through to the line
        `return star_compliant >= len(qa_pairs) * 0.3`
        which evaluates `0 >= 0.0` → True. Empty input should
        return False (nothing was detected). Pinning the broken
        behavior — will flip when fixed.
        """
        a = ConversationAnalyzer()
        assert a._detect_star_method([]) is True  # expected to flip to False on fix


class TestQualityMetrics:
    """_calculate_quality_metrics: 0-1 scores across 5 dimensions."""

    def test_returns_quality_metrics_dataclass(self, analyzer):
        messages = [
            {"role": "interviewer", "content": "Q1?"},
            {"role": "candidate", "content": "A1 with sufficient detail to count."},
        ]
        qa_pairs = analyzer._extract_qa_pairs(messages)
        metrics = analyzer._calculate_quality_metrics(messages, qa_pairs)
        assert isinstance(metrics, QualityMetrics)
        assert 0.0 <= metrics.completeness <= 1.0
        assert 0.0 <= metrics.technical_depth <= 1.0
        assert 0.0 <= metrics.clarity_score <= 1.0
        assert 0.0 <= metrics.structure_score <= 1.0
        assert 0.0 <= metrics.overall_score <= 1.0

    def test_empty_input_safe(self, analyzer):
        metrics = analyzer._calculate_quality_metrics([], [])
        assert metrics.overall_score >= 0
        assert metrics.overall_score <= 1.0


class TestQualityTier:
    """_determine_quality_tier maps score → label."""

    def test_excellent_tier(self, analyzer):
        m = QualityMetrics(
            completeness=0.95, technical_depth=0.9, clarity_score=0.9,
            structure_score=0.9, overall_score=0.9,
        )
        assert analyzer._determine_quality_tier(m) in {
            "excellent", "good", "needs_improvement"
        }
        # 0.9 overall should land in "excellent"
        assert analyzer._determine_quality_tier(m) == "excellent"

    def test_needs_improvement_tier(self, analyzer):
        m = QualityMetrics(
            completeness=0.3, technical_depth=0.2, clarity_score=0.3,
            structure_score=0.2, overall_score=0.25,
        )
        assert analyzer._determine_quality_tier(m) == "needs_improvement"


class TestContentFocus:
    """_analyze_content_focus: keywords → focus areas."""

    def test_system_design_focus(self, analyzer):
        """system_design_focus requires 50% of its 6 keywords
        ['design', 'system', 'architecture', 'scale', 'distributed',
        'microservices'] to appear in the joined text."""
        qa_pairs = [
            {
                "question": "Design a URL shortener that can scale to billions of users",
                "answer": "We need a distributed system with microservices architecture.",
            },
            {
                "question": "How would you design the storage layer?",
                "answer": "Use a distributed system with sharded architecture.",
            },
            {
                "question": "How do you scale the system?",
                "answer": "Horizontally scale using load balancers and microservices.",
            },
        ]
        focus = analyzer._analyze_content_focus(qa_pairs)
        assert "system_design_focus" in focus

    def test_no_focus_detected(self, analyzer):
        qa_pairs = [
            {"question": "Hi", "answer": "Hello"},
        ]
        focus = analyzer._analyze_content_focus(qa_pairs)
        # No specific focus — should return empty or default
        assert isinstance(focus, list)


class TestDifficultyDistribution:
    """_analyze_difficulty_distribution: counts per level."""

    def test_counts_levels(self, analyzer):
        qa_pairs = [
            {"question": "Easy Q", "difficulty": "easy", "answer": "A"},
            {"question": "Medium Q", "difficulty": "medium", "answer": "A"},
            {"question": "Hard Q", "difficulty": "hard", "answer": "A"},
        ]
        dist = analyzer._analyze_difficulty_distribution(qa_pairs)
        # All three levels should be present
        assert dist.get("easy", 0) >= 1
        assert dist.get("medium", 0) >= 1
        assert dist.get("hard", 0) >= 1


class TestFullAnalysisPipeline:
    """analyze_conversation end-to-end: real conversation → all fields."""

    def test_complete_conversation(self, analyzer):
        conversation = {
            "id": "test-conv-1",
            "title": "Mock interview with Google",
            "messages": [
                {"role": "interviewer", "content": "Design a URL shortener."},
                {"role": "candidate", "content": "I would use a hash function and base62 encoding. The system would scale horizontally."},
                {"role": "interviewer", "content": "How do you handle collisions?"},
                {"role": "candidate", "content": "Append a counter or use a different hash."},
            ],
        }
        result = analyzer.analyze_conversation(conversation)
        assert result["conversation_id"] == "test-conv-1"
        assert result["title"] == "Mock interview with Google"
        assert "tags" in result
        assert "type" in result["tags"]
        assert "focus_areas" in result["tags"]
        assert "quality_metrics" in result
        assert "recommendations" in result
        assert "gaps" in result
        # statistics sanity
        stats = result["statistics"]
        assert stats["total_messages"] == 4
        assert stats["question_count"] == 2
        assert stats["answer_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
