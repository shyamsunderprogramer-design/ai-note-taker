"""
performance_analyzer.py - Interview Performance Insights

Phase 2 Task #32: Analyze interview answers against best practices

Features:
- STAR method detection (Situation, Task, Action, Result)
- Code quality scoring for technical answers
- Speaking pace analysis
- Filler word tracking
- Answer structure scoring

Usage:
    from performance_analyzer import analyzer
    analysis = analyzer.analyze_answer(answer_text, question_type)
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger("performance_analyzer")


@dataclass
class STARAnalysis:
    """STAR method analysis results"""
    has_situation: bool
    has_task: bool
    has_action: bool
    has_result: bool
    completeness_score: float
    suggestions: List[str]


@dataclass
class CodeQualityMetrics:
    """Code quality analysis"""
    has_code: bool
    code_blocks: int
    language_detected: Optional[str]
    complexity_score: float
    best_practices_score: float
    issues: List[str]


@dataclass
class SpeakingMetrics:
    """Speaking pattern analysis"""
    word_count: int
    sentence_count: int
    avg_words_per_sentence: float
    filler_word_count: int
    filler_word_ratio: float
    pace_assessment: str  # "too_fast", "good", "too_slow"


class PerformanceAnalyzer:
    """
    Analyze interview answers for quality and best practices.
    """

    # STAR method detection patterns
    STAR_PATTERNS = {
        "situation": [
            r'\bwhen\b', r'\bduring\b', r'\bwhile\b', r'\bat\s+\w+',
            r'\bin\s+\w+', r'\bthere\s+was\b', r'\bwe\s+had\b',
            r'\bpreviously\b', r'\bformerly\b', r'\bbackground\b',
            r'\bcontext\b', r'\bsituation\b'
        ],
        "task": [
            r'\bi\s+had\s+to\b', r'\bmy\s+responsibility\b', r'\bi\s+was\s+asked\b',
            r'\bneeded\s+to\b', r'\brequired\s+to\b', r'\bmy\s+task\s+was\b',
            r'\bi\s+needed\b', r'\bchallenge\s+was\b', r'\bobjective\s+was\b',
            r'\bgoal\s+was\b', r'\bmanaged\b', r'\blead\b',
            r'\bi\s+was\s+responsible\b'
        ],
        "action": [
            r'\bi\s+did\b', r'\bi\s+implemented\b', r'\bi\s+created\b',
            r'\bi\s+worked\b', r'\bi\s+led\b', r'\bi\s+suggested\b',
            r'\bi\s+developed\b', r'\bi\s+designed\b', r'\bi\s+built\b',
            r'\bi\s+architected\b', r'\bi\s+coordinated\b', r'\bi\s+initiated\b',
            r'\bi\s+decided\b', r'\bi\s+chose\b', r'\bso\s+i\b'
        ],
        "result": [
            r'\bresult\b', r'\boutcome\b', r'\bended\s+up\b', r'\bachieved\b',
            r'\bsuccessfully\b', r'\bimproved\s+by\b', r'\bincreased\b',
            r'\bdecreased\b', r'\bsaved\b', r'\breduced\b', r'\benhanced\b',
            r'\bmetrics\b', r'\bimpact\b', r'\bvalue\b', r'\blearned\b',
            r'\bconclusion\b', r'\bultimately\b', r'\bfinally\b'
        ]
    }

    # Filler words to track
    FILLER_WORDS = [
        "um", "uh", "ah", "er", "like", r"you\s+know",
        r"sort\s+of", r"kind\s+of", "basically", "literally",
        "actually", "honestly", "so", "well", "right"
    ]

    # Code indicators
    CODE_INDICATORS = [
        r'```[\s\S]*?```',  # Markdown code blocks
        r'`[^`]+`',          # Inline code
        r'\b(def|class|function|const|let|var)\b',
        r'\b(if|else|for|while|return)\s*\(',
        r'\{[\s\S]*?\}',      # Curly braces blocks
        r'\b(O\(n\)|O\(log\s*n\)|O\(n²\)|time\s+complexity)\b'
    ]

    # Language patterns
    LANGUAGE_PATTERNS = {
        "python": [r'\bdef\s+\w+\s*\(', r'\bprint\s*\(', r'\bimport\s+\w+'],
        "javascript": [r'\bconst\s+\w+\s*=', r'\bfunction\s*\w*\s*\(', r'\b=>\s*\{'],
        "java": [r'\bpublic\s+class\b', r'\bSystem\.out\.println\b'],
        "go": [r'\bfunc\s+\w+\s*\(', r'\bpackage\s+\w+'],
        "rust": [r'\bfn\s+\w+\s*\(', r'\blet\s+mut\b'],
        "cpp": [r'#include\s*<', r'\bstd::', r'\bint\s+main\s*\(']
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self.compiled_star = {
            component: [re.compile(p, re.IGNORECASE) for p in patterns]
            for component, patterns in self.STAR_PATTERNS.items()
        }

        self.filler_pattern = re.compile(
            r'\b(' + '|'.join(self.FILLER_WORDS) + r')\b',
            re.IGNORECASE
        )

        self.code_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.CODE_INDICATORS
        ]

    def analyze_answer(
        self,
        answer_text: str,
        question_type: str = "behavioral"
    ) -> Dict:
        """
        Comprehensive answer analysis.

        Args:
            answer_text: The answer to analyze
            question_type: "behavioral", "technical", "system_design"

        Returns:
            Complete analysis with scores and recommendations
        """
        if not answer_text or len(answer_text.strip()) < 10:
            return self._empty_analysis()

        # STAR method analysis (for behavioral)
        star_analysis = self.analyze_star_method(answer_text)

        # Code quality (for technical)
        code_quality = self.analyze_code_quality(answer_text)

        # Speaking metrics
        speaking = self.analyze_speaking_patterns(answer_text)

        # Structure analysis
        structure = self.analyze_structure(answer_text)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            star_analysis, code_quality, speaking, structure, question_type
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            star_analysis, code_quality, speaking, structure, question_type
        )

        return {
            "answer_length": len(answer_text),
            "word_count": speaking.word_count,
            "question_type": question_type,
            "star_analysis": {
                "has_situation": star_analysis.has_situation,
                "has_task": star_analysis.has_task,
                "has_action": star_analysis.has_action,
                "has_result": star_analysis.has_result,
                "completeness_score": round(star_analysis.completeness_score, 2),
                "components_found": sum([
                    star_analysis.has_situation,
                    star_analysis.has_task,
                    star_analysis.has_action,
                    star_analysis.has_result
                ]),
                "missing_components": self._get_missing_star_components(star_analysis)
            },
            "code_quality": {
                "has_code": code_quality.has_code,
                "code_blocks": code_quality.code_blocks,
                "language": code_quality.language_detected,
                "complexity_score": round(code_quality.complexity_score, 2),
                "best_practices_score": round(code_quality.best_practices_score, 2),
                "issues": code_quality.issues
            },
            "speaking_patterns": {
                "word_count": speaking.word_count,
                "sentence_count": speaking.sentence_count,
                "avg_words_per_sentence": round(speaking.avg_words_per_sentence, 1),
                "filler_word_count": speaking.filler_word_count,
                "filler_word_ratio": round(speaking.filler_word_ratio * 100, 1),
                "pace_assessment": speaking.pace_assessment
            },
            "structure": {
                "has_introduction": structure.get("has_introduction", False),
                "has_conclusion": structure.get("has_conclusion", False),
                "uses_examples": structure.get("uses_examples", False),
                "organized": structure.get("organized", False)
            },
            "overall_score": round(overall_score, 2),
            "quality_tier": self._get_quality_tier(overall_score),
            "recommendations": recommendations,
            "strengths": self._identify_strengths(star_analysis, code_quality, speaking, structure),
            "weaknesses": self._identify_weaknesses(star_analysis, code_quality, speaking, structure)
        }

    def analyze_star_method(self, text: str) -> STARAnalysis:
        """Analyze if answer follows STAR method"""
        text_lower = text.lower()

        has_situation = any(
            pattern.search(text_lower)
            for pattern in self.compiled_star["situation"]
        )
        has_task = any(
            pattern.search(text_lower)
            for pattern in self.compiled_star["task"]
        )
        has_action = any(
            pattern.search(text_lower)
            for pattern in self.compiled_star["action"]
        )
        has_result = any(
            pattern.search(text_lower)
            for pattern in self.compiled_star["result"]
        )

        # Calculate completeness score
        components = [has_situation, has_task, has_action, has_result]
        completeness = sum(components) / 4.0

        # Generate suggestions
        suggestions = []
        if not has_situation:
            suggestions.append("Add context by describing the situation first")
        if not has_task:
            suggestions.append("Clarify your specific responsibility or challenge")
        if not has_action:
            suggestions.append("Describe what YOU did (not just the team)")
        if not has_result:
            suggestions.append("Include specific outcomes and quantifiable results")

        return STARAnalysis(
            has_situation=has_situation,
            has_task=has_task,
            has_action=has_action,
            has_result=has_result,
            completeness_score=completeness,
            suggestions=suggestions
        )

    def analyze_code_quality(self, text: str) -> CodeQualityMetrics:
        """Analyze code quality in technical answers"""
        has_code = False
        code_blocks = 0
        language = None
        issues = []
        complexity_score = 0.0
        best_practices_score = 0.0

        # Detect code blocks
        code_block_matches = re.findall(r'```[\s\S]*?```', text)
        inline_code_matches = re.findall(r'`[^`]+`', text)

        code_blocks = len(code_block_matches) + len(inline_code_matches)
        has_code = code_blocks > 0

        if has_code:
            # Detect language
            for lang, patterns in self.LANGUAGE_PATTERNS.items():
                if any(re.search(p, text) for p in patterns):
                    language = lang
                    break

            # Check for complexity indicators
            complexity_indicators = [
                (r'\b(recursion|recursive)\b', "uses recursion"),
                (r'\b(dynamic\s+programming|memoization)\b', "uses advanced techniques"),
                (r'O\(n[²\^2]\)|O\(2\^n\)|O\(n!\)|O\(n\s*\^\s*2\)', "complex time complexity"),
            ]

            complexity_score = sum(
                0.25 for pattern, _ in complexity_indicators
                if re.search(pattern, text, re.IGNORECASE)
            )

            # Check for best practices
            best_practice_indicators = [
                (r'\b(error\s+handling|try\s+catch|try\s*:|except\b|exception)\b', "error handling"),
                (r'\b(unit\s+test|test\s+case|assert)\b', "testing"),
                (r'\b(documentation|comment|docstring|#\s)', "documentation"),
                (r'\b(edge\s+case|corner\s+case|boundary)\b', "edge cases"),
            ]

            best_practices_score = sum(
                0.25 for pattern, _ in best_practice_indicators
                if re.search(pattern, text, re.IGNORECASE)
            )

        # Check for issues (even in plain text answers)
        issue_patterns = [
            (r'\b(goto)\b', "Avoid using goto statements"),
            (r'\b(var\s+\w+\s*=)[^;]*;\s*\1', "Variable redeclaration"),
        ]

        for pattern, message in issue_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(message)

        return CodeQualityMetrics(
            has_code=has_code,
            code_blocks=code_blocks,
            language_detected=language,
            complexity_score=min(complexity_score if has_code else 0.0, 1.0),
            best_practices_score=min(best_practices_score if has_code else 0.0, 1.0),
            issues=issues
        )

    def analyze_speaking_patterns(self, text: str) -> SpeakingMetrics:
        """Analyze speaking patterns in answer"""
        words = text.split()
        word_count = len(words)

        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])

        avg_words_per_sentence = (
            word_count / max(sentence_count, 1)
        )

        # Count filler words
        filler_matches = self.filler_pattern.findall(text.lower())
        filler_count = len(filler_matches)
        filler_ratio = filler_count / max(word_count, 1)

        # Assess pace
        if avg_words_per_sentence > 25:
            pace = "too_fast"
        elif avg_words_per_sentence < 8:
            pace = "too_slow"
        else:
            pace = "good"

        return SpeakingMetrics(
            word_count=word_count,
            sentence_count=sentence_count,
            avg_words_per_sentence=avg_words_per_sentence,
            filler_word_count=filler_count,
            filler_word_ratio=filler_ratio,
            pace_assessment=pace
        )

    def analyze_structure(self, text: str) -> Dict:
        """Analyze answer structure"""
        text_lower = text.lower()

        # Check for introduction
        has_intro = any(
            phrase in text_lower[:200]
            for phrase in ["i'd", "i would", "sure", "absolutely", "so", "well"]
        )

        # Check for conclusion
        has_conclusion = any(
            phrase in text_lower[-200:]
            for phrase in ["in conclusion", "to summarize", "overall", "ultimately"]
        ) or text_lower.rstrip().endswith('.')

        # Check for examples
        uses_examples = bool(re.search(
            r'\b(for\s+example|such\s+as|like\s+when|instance)\b',
            text_lower
        ))

        # Check organization (numbered lists, transitions)
        organized = bool(re.search(
            r'\b(first|second|third|1\.|2\.|3\.|next|then|finally)\b',
            text_lower
        ))

        return {
            "has_introduction": has_intro,
            "has_conclusion": has_conclusion,
            "uses_examples": uses_examples,
            "organized": organized
        }

    def _calculate_overall_score(
        self,
        star: STARAnalysis,
        code: CodeQualityMetrics,
        speaking: SpeakingMetrics,
        structure: Dict,
        question_type: str
    ) -> float:
        """Calculate overall answer quality score"""
        scores = []
        weights = []

        # STAR score (important for behavioral)
        if question_type == "behavioral":
            scores.append(star.completeness_score)
            weights.append(0.35)

        # Code quality (important for technical)
        if question_type in ["technical", "system_design"]:
            if code.has_code:
                code_score = (code.complexity_score + code.best_practices_score) / 2
                scores.append(code_score)
                weights.append(0.30)

        # Speaking clarity
        clarity = 1.0 - min(speaking.filler_word_ratio * 5, 1.0)  # Penalize fillers
        if speaking.pace_assessment == "good":
            clarity += 0.1
        scores.append(clarity)
        weights.append(0.20)

        # Structure score
        structure_score = sum([
            structure.get("has_introduction", False),
            structure.get("has_conclusion", False),
            structure.get("uses_examples", False),
            structure.get("organized", False)
        ]) / 4.0
        scores.append(structure_score)
        weights.append(0.15)

        # Weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return (weighted_sum / total_weight) * 100

        return 50.0

    def _get_quality_tier(self, score: float) -> str:
        """Convert score to quality tier"""
        if score >= 80:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 50:
            return "average"
        return "needs_improvement"

    def _get_missing_star_components(self, star: STARAnalysis) -> List[str]:
        """List missing STAR components"""
        missing = []
        if not star.has_situation:
            missing.append("situation")
        if not star.has_task:
            missing.append("task")
        if not star.has_action:
            missing.append("action")
        if not star.has_result:
            missing.append("result")
        return missing

    def _generate_recommendations(
        self,
        star: STARAnalysis,
        code: CodeQualityMetrics,
        speaking: SpeakingMetrics,
        structure: Dict,
        question_type: str
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        # STAR recommendations
        if question_type == "behavioral":
            if star.completeness_score < 0.75:
                recs.append("Use STAR format: Situation, Task, Action, Result")
            if not star.has_result:
                recs.append("Include quantifiable results (e.g., 'reduced latency by 50%')")

        # Code recommendations
        if question_type in ["technical", "system_design"]:
            if code.has_code and code.best_practices_score < 0.5:
                recs.append("Mention error handling and edge cases in your code")
            if not code.has_code and question_type == "technical":
                recs.append("Consider providing code examples to support your answer")

        # Speaking recommendations
        if speaking.filler_word_ratio > 0.05:
            recs.append(f"Reduce filler words (found {speaking.filler_word_count} instances)")
        if speaking.pace_assessment == "too_fast":
            recs.append("Slow down - your sentences are quite long")
        if speaking.pace_assessment == "too_slow":
            recs.append("Add more detail to your answers")

        # Structure recommendations
        if not structure.get("organized"):
            recs.append("Use transitions like 'First', 'Next', 'Finally' to organize your answer")

        return recs[:3]  # Top 3 recommendations

    def _identify_strengths(
        self,
        star: STARAnalysis,
        code: CodeQualityMetrics,
        speaking: SpeakingMetrics,
        structure: Dict
    ) -> List[str]:
        """Identify answer strengths"""
        strengths = []

        if star.completeness_score >= 0.75:
            strengths.append("Strong STAR structure")
        if code.has_code and code.best_practices_score >= 0.5:
            strengths.append("Good code quality and practices")
        if speaking.filler_word_ratio < 0.03:
            strengths.append("Clear communication with minimal fillers")
        if structure.get("organized"):
            strengths.append("Well-organized answer structure")

        return strengths

    def _identify_weaknesses(
        self,
        star: STARAnalysis,
        code: CodeQualityMetrics,
        speaking: SpeakingMetrics,
        structure: Dict
    ) -> List[str]:
        """Identify answer weaknesses"""
        weaknesses = []

        if star.completeness_score < 0.5:
            weaknesses.append("Incomplete STAR structure")
        if speaking.filler_word_ratio > 0.08:
            weaknesses.append("High filler word usage")
        if speaking.word_count < 50:
            weaknesses.append("Answer may be too brief")
        if not structure.get("uses_examples"):
            weaknesses.append("Lack of specific examples")

        return weaknesses

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "answer_length": 0,
            "word_count": 0,
            "question_type": "unknown",
            "star_analysis": {
                "has_situation": False,
                "has_task": False,
                "has_action": False,
                "has_result": False,
                "completeness_score": 0.0,
                "components_found": 0,
                "missing_components": []
            },
            "code_quality": {
                "has_code": False,
                "code_blocks": 0,
                "language": None,
                "complexity_score": 0.0,
                "best_practices_score": 0.0,
                "issues": []
            },
            "speaking_patterns": {
                "word_count": 0,
                "sentence_count": 0,
                "avg_words_per_sentence": 0.0,
                "filler_word_count": 0,
                "filler_word_ratio": 0.0,
                "pace_assessment": "unknown"
            },
            "structure": {
                "has_introduction": False,
                "has_conclusion": False,
                "uses_examples": False,
                "organized": False
            },
            "overall_score": 0.0,
            "quality_tier": "unknown",
            "recommendations": [],
            "strengths": [],
            "weaknesses": []
        }


# Global instance
analyzer = PerformanceAnalyzer()


def analyze_answer(answer_text: str, question_type: str = "behavioral") -> Dict:
    """Analyze answer - convenience function"""
    return analyzer.analyze_answer(answer_text, question_type)


def batch_analyze_answers(answers: List[Dict]) -> List[Dict]:
    """Analyze multiple answers - convenience function"""
    return [
        analyzer.analyze_answer(a.get("text", ""), a.get("type", "behavioral"))
        for a in answers
    ]
