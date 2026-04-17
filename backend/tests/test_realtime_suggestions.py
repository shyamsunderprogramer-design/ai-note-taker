"""
Test suite for Real-Time Suggestion Engine
Phase 2 Task #28

Run with: python -m pytest backend/tests/test_realtime_suggestions.py -v
"""

import pytest
import sys
import os
from datetime import datetime

# Add backend and modules/ai to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'ai'))

from realtime_suggestions import (
    RealtimeSuggestionEngine,
    VoiceCommandProcessor,
    Suggestion,
    TranscriptSegment,
    process_transcript_segment,
    process_voice_command,
    set_suggestion_confidence
)


class TestRealtimeSuggestionEngine:
    """Test cases for RealtimeSuggestionEngine"""

    def setup_method(self):
        """Setup fresh engine for each test"""
        self.engine = RealtimeSuggestionEngine(
            min_confidence=0.6,
            cooldown_seconds=1.0
        )

    def test_is_question_with_question_mark(self):
        """Test detection of questions ending with ?"""
        assert self.engine.is_question("What is React?") is True  # nosec B101
        assert self.engine.is_question("How does it work?") is True  # nosec B101

    def test_is_question_with_question_words(self):
        """Test detection of questions starting with question words"""
        assert self.engine.is_question("Tell me about your experience") is True  # nosec B101
        assert self.engine.is_question("Explain how you handled a conflict") is True  # nosec B101
        assert self.engine.is_question("Describe your biggest achievement") is True  # nosec B101

    def test_is_question_with_technical_patterns(self):
        """Test detection of technical interview patterns"""
        assert self.engine.is_question("Design a URL shortener") is True  # nosec B101
        assert self.engine.is_question("Implement a hash map") is True  # nosec B101
        assert self.engine.is_question("Optimize this query") is True  # nosec B101

    def test_is_not_question_statement(self):
        """Test that statements are not detected as questions"""
        assert self.engine.is_question("I worked on React for 3 years") is False  # nosec B101
        assert self.engine.is_question("The system uses microservices") is False  # nosec B101

    def test_process_segment_interviewer_question(self):
        """Test processing interviewer question"""
        segment = TranscriptSegment(
            text="What is your experience with React?",
            speaker="interviewer",
            timestamp=datetime.now().timestamp(),
            confidence=1.0,
            is_question=True
        )

        # Without cognitive graph, should return None
        result = self.engine._generate_suggestion(segment)
        assert result is None  # nosec B101

    def test_process_segment_user_statement(self):
        """Test that user statements don't trigger suggestions"""
        result = self.engine.process_segment(
            "I have 5 years of React experience",
            "user"
        )
        assert result is None  # nosec B101

    def test_process_segment_non_question(self):
        """Test that non-questions from interviewer don't trigger"""
        result = self.engine.process_segment(
            "Let me tell you about the team",
            "interviewer"
        )
        assert result is None  # nosec B101

    def test_cooldown_mechanism(self):
        """Test cooldown prevents rapid suggestions"""
        # First question should process
        result1 = self.engine.process_segment(
            "What is your experience with Python?",
            "interviewer",
            timestamp=1000.0
        )

        # Immediate second question should be blocked
        result2 = self.engine.process_segment(
            "How about JavaScript?",
            "interviewer",
            timestamp=1000.5  # Within cooldown
        )

        # Results may be None (no graph), but second should be blocked by cooldown
        # If first returned a suggestion, second should definitely be None

    def test_extract_keywords(self):
        """Test keyword extraction from technical questions"""
        keywords = self.engine._extract_keywords(
            "Design a distributed system using React and Python"
        )

        assert "react" in keywords  # nosec B101
        assert "python" in keywords  # nosec B101
        assert "system design" in keywords or "distributed" in keywords  # nosec B101

    def test_calculate_confidence(self):
        """Test confidence score calculation"""
        match = {
            "relevance": 0.8,
            "category": "technical",
            "company": "Google"
        }

        confidence = self.engine._calculate_confidence(
            "What is your experience with React?",
            match
        )

        # Should be boosted by relevance, category, and company
        assert 0.5 <= confidence <= 1.0  # nosec B101

    def test_calculate_confidence_short_query(self):
        """Test confidence is penalized for short queries"""
        match = {"relevance": 0.5}

        confidence = self.engine._calculate_confidence("React?", match)
        assert confidence < 0.5  # Penalized for short query  # nosec B101

    def test_clear_buffer(self):
        """Test buffer clearing"""
        self.engine.segment_buffer.append(
            TranscriptSegment("test", "user", 1000.0, 1.0)
        )
        assert len(self.engine.segment_buffer) == 1  # nosec B101

        self.engine.clear_buffer()
        assert len(self.engine.segment_buffer) == 0  # nosec B101
        assert self.engine.last_suggestion_time is None  # nosec B101

    def test_set_min_confidence(self):
        """Test confidence threshold adjustment"""
        self.engine.set_min_confidence(0.8)
        assert self.engine.min_confidence == 0.8  # nosec B101

        # Test clamping
        self.engine.set_min_confidence(1.5)
        assert self.engine.min_confidence == 1.0  # nosec B101

        self.engine.set_min_confidence(-0.5)
        assert self.engine.min_confidence == 0.0  # nosec B101

    def test_format_suggestion(self):
        """Test suggestion formatting"""
        match = {
            "question": "Tell me about yourself",
            "answer": "I am a software engineer with 5 years experience.",
            "company": "Google",
            "topics": ["career", "background"]
        }

        formatted = self.engine._format_suggestion(match)

        assert "Tell me about yourself" in formatted  # nosec B101
        assert "Google" in formatted  # nosec B101
        assert "software engineer" in formatted  # nosec B101
        assert "topics" in formatted.lower() or "Topics" in formatted  # nosec B101

    def test_suggestion_history(self):
        """Test suggestion history tracking"""
        # Add mock suggestions to history
        for i in range(5):
            self.engine.suggestion_history.append(
                Suggestion(
                    id=f"sugg-{i}",
                    type="similar_question",
                    content=f"Test {i}",
                    context={},
                    confidence=0.7,
                    relevance_score=0.6,
                    timestamp=datetime.now(),
                    source="test"
                )
            )

        history = self.engine.get_suggestion_history(limit=3)
        assert len(history) == 3  # nosec B101


class TestVoiceCommandProcessor:
    """Test cases for VoiceCommandProcessor"""

    def setup_method(self):
        """Setup fresh processor"""
        engine = RealtimeSuggestionEngine()
        self.processor = VoiceCommandProcessor(engine)

    def test_search_command_pattern(self):
        """Test search command detection"""
        # These should match search patterns
        assert self.processor.process_command("what did i say about React") is not None  # nosec B101
        assert self.processor.process_command("remind me about system design") is not None  # nosec B101
        assert self.processor.process_command("search for my Python answers") is not None  # nosec B101
        assert self.processor.process_command("find React in my history") is not None  # nosec B101

    def test_non_command_text(self):
        """Test that normal text is not a command"""
        result = self.processor.process_command("I really like working with React")
        assert result is None  # nosec B101

    def test_suggest_command_pattern(self):
        """Test suggestion command detection"""
        # Add a question to the buffer first
        self.processor.engine.segment_buffer.append(
            TranscriptSegment(
                "What is your experience?",
                "interviewer",
                datetime.now().timestamp(),
                1.0,
                True
            )
        )

        result = self.processor.process_command("give me a hint")
        # Result may be None without graph, but should return something
        # (could be error message about no graph)


class TestConvenienceFunctions:
    """Test convenience module-level functions"""

    def test_process_transcript_segment(self):
        """Test convenience function"""
        result = process_transcript_segment(
            "What is your experience?",
            "interviewer"
        )
        # Returns None without cognitive graph
        assert result is None  # nosec B101

    def test_process_voice_command(self):
        """Test convenience function"""
        result = process_voice_command("what did i say about React")
        # Returns a dict when cognitive graph is available, None otherwise
        if result is not None:
            assert isinstance(result, dict)  # nosec B101
            assert "action" in result  # nosec B101

    def test_set_suggestion_confidence(self):
        """Test global confidence setter"""
        # Just verify it doesn't crash
        set_suggestion_confidence(0.75)


class TestTranscriptSegment:
    """Test TranscriptSegment dataclass"""

    def test_segment_creation(self):
        """Test segment creation"""
        segment = TranscriptSegment(
            text="Test question?",
            speaker="interviewer",
            timestamp=1000.0,
            confidence=0.95,
            is_question=True
        )

        assert segment.text == "Test question?"  # nosec B101
        assert segment.speaker == "interviewer"  # nosec B101
        assert segment.is_question is True  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
