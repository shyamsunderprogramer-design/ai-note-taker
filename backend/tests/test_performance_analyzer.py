"""
Test suite for Interview Performance Analyzer
Phase 2 Task #32

Run with: python -m pytest backend/tests/test_performance_analyzer.py -v
"""

import pytest
import sys
import os

# Add backend and modules/ai to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'ai'))

from performance_analyzer import (
    PerformanceAnalyzer,
    STARAnalysis,
    CodeQualityMetrics,
    SpeakingMetrics,
    analyze_answer,
    batch_analyze_answers
)


class TestSTARMethodDetection:
    """Test cases for STAR method detection"""

    def setup_method(self):
        """Setup fresh analyzer"""
        self.analyzer = PerformanceAnalyzer()

    def test_complete_star_answer(self):
        """Test detection of complete STAR answer"""
        answer = """
        At my previous company, we had a major outage affecting 1000 users.
        I was responsible for fixing the database issue.
        I implemented a caching layer and optimized the queries.
        This resulted in a 50% reduction in response time.
        """

        star = self.analyzer.analyze_star_method(answer)

        assert star.has_situation is True
        assert star.has_task is True
        assert star.has_action is True
        assert star.has_result is True
        assert star.completeness_score == 1.0

    def test_missing_result(self):
        """Test detection of missing result component"""
        answer = """
        When I was at Company X, we had a challenging project.
        My task was to redesign the frontend.
        I worked on implementing React components.
        """

        star = self.analyzer.analyze_star_method(answer)

        assert star.has_situation is True
        assert star.has_task is True
        assert star.has_action is True
        assert star.has_result is False
        assert star.completeness_score == 0.75
        assert "quantifiable results" in star.suggestions[0].lower()

    def test_missing_action(self):
        """Test detection of missing action component"""
        answer = """
        Previously at my job, we had a scaling issue.
        I needed to improve performance.
        Ultimately we achieved 99% uptime.
        """

        star = self.analyzer.analyze_star_method(answer)

        assert star.has_situation is True
        assert star.has_task is True
        assert star.has_action is False
        assert star.has_result is True

    def test_incomplete_star(self):
        """Test detection of incomplete STAR answer"""
        answer = "I have experience with React and JavaScript."

        star = self.analyzer.analyze_star_method(answer)

        assert star.completeness_score < 0.5
        assert len(star.suggestions) > 0

    def test_situation_keywords(self):
        """Test situation keyword detection"""
        answer = "At my previous company, we faced a challenge..."
        star = self.analyzer.analyze_star_method(answer)
        assert star.has_situation is True

        answer = "During my internship, there was an issue..."
        star = self.analyzer.analyze_star_method(answer)
        assert star.has_situation is True

    def test_action_keywords(self):
        """Test action keyword detection"""
        answer = "I implemented a solution and built the system..."
        star = self.analyzer.analyze_star_method(answer)
        assert star.has_action is True


class TestCodeQualityAnalysis:
    """Test cases for code quality analysis"""

    def setup_method(self):
        self.analyzer = PerformanceAnalyzer()

    def test_detect_code_blocks(self):
        """Test detection of code blocks"""
        answer = """
        Here's my solution:
        ```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        ```
        """

        code_quality = self.analyzer.analyze_code_quality(answer)

        assert code_quality.has_code is True
        assert code_quality.code_blocks >= 1
        assert code_quality.language_detected == "python"

    def test_detect_inline_code(self):
        """Test detection of inline code"""
        answer = "Use `array.map()` to transform the data"

        code_quality = self.analyzer.analyze_code_quality(answer)

        assert code_quality.has_code is True
        assert code_quality.code_blocks >= 1

    def test_no_code_detection(self):
        """Test that text without code is detected"""
        answer = "I have experience with various programming languages."

        code_quality = self.analyzer.analyze_code_quality(answer)

        assert code_quality.has_code is False
        assert code_quality.code_blocks == 0
        assert code_quality.complexity_score == 0.0

    def test_language_detection_javascript(self):
        """Test JavaScript language detection"""
        answer = """
        ```javascript
const result = data.filter(x => x > 0).map(x => x * 2);
        ```
        """

        code_quality = self.analyzer.analyze_code_quality(answer)
        assert code_quality.language_detected == "javascript"

    def test_complexity_detection(self):
        """Test detection of code complexity"""
        answer = """
        ```python
# O(n²) solution
def find_duplicates(arr):
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j]:
                return True
    return False
        ```
        """

        code_quality = self.analyzer.analyze_code_quality(answer)
        assert code_quality.complexity_score > 0

    def test_best_practices_detection(self):
        """Test detection of best practices"""
        answer = """
        ```python
def process_data(data):
    try:
        result = transform(data)
        return result
    except ValueError as e:
        logger.error(f"Error: {e}")
        return None
        ```
        """

        code_quality = self.analyzer.analyze_code_quality(answer)
        assert code_quality.best_practices_score > 0

    def test_issue_detection_goto(self):
        """Test detection of code issues"""
        answer = "I used goto statements to control flow"

        code_quality = self.analyzer.analyze_code_quality(answer)
        assert any("goto" in issue.lower() for issue in code_quality.issues)


class TestSpeakingPatternAnalysis:
    """Test cases for speaking pattern analysis"""

    def setup_method(self):
        self.analyzer = PerformanceAnalyzer()

    def test_filler_word_detection(self):
        """Test detection of filler words"""
        answer = "Um, I think, uh, the solution is, like, basically correct."

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.filler_word_count > 0
        assert speaking.filler_word_ratio > 0

    def test_pace_assessment_good(self):
        """Test good pace assessment"""
        # Medium length sentences = good pace
        answer = "I implemented the feature. It took about three days. The code works well."

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.pace_assessment == "good"

    def test_pace_assessment_too_fast(self):
        """Test too fast pace detection"""
        # Long sentences = too fast
        answer = """I implemented the feature which was quite challenging because
        there were many requirements that needed to be satisfied and I had to
        consider various edge cases while maintaining backward compatibility."""

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.avg_words_per_sentence > 25
        assert speaking.pace_assessment == "too_fast"

    def test_pace_assessment_too_slow(self):
        """Test too slow pace detection"""
        # Very short sentences = too slow
        answer = "I did it. It works. Done."

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.avg_words_per_sentence < 8
        assert speaking.pace_assessment == "too_slow"

    def test_word_count(self):
        """Test word counting"""
        answer = "This is a test answer with eight words."

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.word_count == 8

    def test_sentence_count(self):
        """Test sentence counting"""
        answer = "First sentence. Second sentence! Third sentence?"

        speaking = self.analyzer.analyze_speaking_patterns(answer)

        assert speaking.sentence_count == 3


class TestStructureAnalysis:
    """Test cases for answer structure analysis"""

    def setup_method(self):
        self.analyzer = PerformanceAnalyzer()

    def test_has_introduction(self):
        """Test introduction detection"""
        answer = "Sure, I'd be happy to tell you about that..."
        structure = self.analyzer.analyze_structure(answer)
        assert structure["has_introduction"] is True

    def test_has_conclusion(self):
        """Test conclusion detection"""
        answer = "In conclusion, this was a valuable experience."
        structure = self.analyzer.analyze_structure(answer)
        assert structure["has_conclusion"] is True

    def test_uses_examples(self):
        """Test example usage detection"""
        answer = "For example, when I worked at Google..."
        structure = self.analyzer.analyze_structure(answer)
        assert structure["uses_examples"] is True

    def test_organized_structure(self):
        """Test organization detection"""
        answer = "First, I analyzed the problem. Then, I implemented the solution. Finally, I tested it."
        structure = self.analyzer.analyze_structure(answer)
        assert structure["organized"] is True


class TestOverallAnalysis:
    """Test cases for complete answer analysis"""

    def setup_method(self):
        self.analyzer = PerformanceAnalyzer()

    def test_complete_behavioral_analysis(self):
        """Test complete behavioral answer analysis"""
        answer = """
        At my previous company, we had a major system outage.
        My task was to restore service within 2 hours.
        I coordinated with the team and implemented a hotfix.
        We restored service in 1 hour, preventing $50k in losses.
        """

        result = self.analyzer.analyze_answer(answer, "behavioral")

        assert result["overall_score"] > 0
        assert result["quality_tier"] in ["excellent", "good", "average", "needs_improvement"]
        assert result["star_analysis"]["completeness_score"] > 0
        assert "recommendations" in result
        assert "strengths" in result
        assert "weaknesses" in result

    def test_technical_answer_analysis(self):
        """Test technical answer analysis"""
        answer = """
        ```python
def fibonacci(n):
    # Handle edge cases
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        ```
        This is O(2^n) time complexity.
        """

        result = self.analyzer.analyze_answer(answer, "technical")

        assert result["code_quality"]["has_code"] is True
        assert result["code_quality"]["language"] == "python"

    def test_short_answer(self):
        """Test handling of very short answers"""
        answer = "Yes"

        result = self.analyzer.analyze_answer(answer, "behavioral")

        assert result["overall_score"] == 0
        assert result["quality_tier"] == "unknown"

    def test_empty_analysis(self):
        """Test empty analysis for invalid input"""
        result = self.analyzer._empty_analysis()

        assert result["word_count"] == 0
        assert result["overall_score"] == 0
        assert result["star_analysis"]["completeness_score"] == 0

    def test_quality_tier_calculation(self):
        """Test quality tier calculation"""
        assert self.analyzer._get_quality_tier(85) == "excellent"
        assert self.analyzer._get_quality_tier(70) == "good"
        assert self.analyzer._get_quality_tier(55) == "average"
        assert self.analyzer._get_quality_tier(40) == "needs_improvement"


class TestBatchProcessing:
    """Test cases for batch analysis"""

    def test_batch_analyze_answers(self):
        """Test batch answer analysis"""
        answers = [
            {"text": "I have experience with React.", "type": "behavioral"},
            {"text": "```python\nprint('hello')\n```", "type": "technical"}
        ]

        results = batch_analyze_answers(answers)

        assert len(results) == 2
        assert all("overall_score" in r for r in results)


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_analyze_answer(self):
        """Test analyze_answer convenience function"""
        result = analyze_answer("I worked on React projects.", "behavioral")
        assert "overall_score" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
