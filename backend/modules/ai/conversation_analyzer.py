"""
conversation_analyzer.py - Automatic Conversation Categorization & Quality Analysis

Phase 2 Task #30: Auto-tag conversations by type and quality

Features:
- Auto-tag conversations by type (practice, mock, real interview)
- Quality metrics (completeness, technical depth, clarity)
- Content analysis (system design focus, algorithm heavy, behavioral only)
- STAR method detection for behavioral answers

Usage:
    from conversation_analyzer import analyzer
    analysis = analyzer.analyze_conversation(conversation_data)
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
from datetime import datetime

logger = logging.getLogger("conversation_analyzer")


@dataclass
class ConversationTags:
    """Tags assigned to a conversation"""
    type: str  # "practice", "mock_interview", "real_interview"
    focus_areas: List[str]  # ["system_design", "algorithms", "behavioral"]
    difficulty_distribution: Dict[str, int]
    is_star_formatted: bool
    quality_tier: str  # "excellent", "good", "needs_improvement"


@dataclass
class QualityMetrics:
    """Quality metrics for a conversation"""
    completeness: float  # 0-1, how complete are answers
    technical_depth: float  # 0-1, depth of technical content
    clarity_score: float  # 0-1, speaking clarity
    structure_score: float  # 0-1, answer organization
    overall_score: float  # 0-1, weighted average


class ConversationAnalyzer:
    """
    Analyze interview conversations for categorization and quality.
    """

    # Conversation type detection patterns
    TYPE_PATTERNS = {
        "practice_session": {
            "keywords": ["practice", "preparing", "studying", "learning", "review"],
            "indicators": ["self_identified"],
            "weight": 0.7
        },
        "mock_interview": {
            "keywords": ["mock", "simulated", "practice interview", "test run"],
            "indicators": ["multiple_speakers", "structured_qa"],
            "weight": 0.8
        },
        "real_interview": {
            "keywords": ["interview at", "interview with", "phone screen", "onsite", "final round"],
            "indicators": ["company_mentioned", "formal_tone"],
            "weight": 0.9
        }
    }

    # Content category detection
    CONTENT_CATEGORIES = {
        "system_design_focus": {
            "threshold": 0.5,  # 50% of questions
            "keywords": ["design", "system", "architecture", "scale", "distributed", "microservices"]
        },
        "algorithm_heavy": {
            "threshold": 0.7,
            "keywords": ["algorithm", "complexity", "optimize", "data structure", "leetcode"]
        },
        "behavioral_only": {
            "threshold": 0.9,
            "keywords": ["tell me about", "describe a time", "give an example", "situation"]
        },
        "frontend_focus": {
            "threshold": 0.5,
            "keywords": ["react", "javascript", "css", "dom", "browser", "ui", "frontend"]
        },
        "backend_focus": {
            "threshold": 0.5,
            "keywords": ["api", "database", "server", "backend", "microservice", "cache"]
        },
        "fullstack_focus": {
            "threshold": 0.4,
            "keywords": ["frontend", "backend", "fullstack", "end-to-end"]
        }
    }

    # STAR method detection patterns
    STAR_PATTERNS = {
        "situation": ["when", "during", "while", "at", "in", "there was", "we had"],
        "task": ["i had to", "my responsibility", "i was asked", "needed to", "required to"],
        "action": ["i did", "i implemented", "i created", "i worked", "i led", "i suggested"],
        "result": ["result", "outcome", "ended up", "achieved", "successfully", "improved by"]
    }

    def __init__(self):
        self.filler_words = ["um", "uh", "like", "you know", "so", "basically", "literally"]

    def analyze_conversation(self, conversation: Dict) -> Dict:
        """
        Analyze a conversation and return comprehensive analysis.

        Args:
            conversation: Dict with messages, title, metadata

        Returns:
            Analysis results with tags, metrics, and recommendations
        """
        messages = conversation.get("messages", [])
        title = conversation.get("title", "")

        if not messages:
            return self._empty_analysis()

        # Extract Q&A pairs
        qa_pairs = self._extract_qa_pairs(messages)

        # Determine conversation type
        conv_type = self._detect_conversation_type(title, messages, qa_pairs)

        # Analyze content focus
        focus_areas = self._analyze_content_focus(qa_pairs)

        # Calculate difficulty distribution
        difficulty_dist = self._analyze_difficulty_distribution(qa_pairs)

        # Check STAR formatting
        star_formatted = self._detect_star_method(qa_pairs)

        # Calculate quality metrics
        quality = self._calculate_quality_metrics(messages, qa_pairs)

        # Determine quality tier
        quality_tier = self._determine_quality_tier(quality)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            qa_pairs, focus_areas, quality, star_formatted
        )

        return {
            "conversation_id": conversation.get("id", "unknown"),
            "title": title,
            "analysis_timestamp": datetime.now().isoformat(),
            "tags": {
                "type": conv_type,
                "focus_areas": focus_areas,
                "difficulty_distribution": difficulty_dist,
                "is_star_formatted": star_formatted,
                "quality_tier": quality_tier
            },
            "quality_metrics": {
                "completeness": round(quality.completeness, 2),
                "technical_depth": round(quality.technical_depth, 2),
                "clarity_score": round(quality.clarity_score, 2),
                "structure_score": round(quality.structure_score, 2),
                "overall_score": round(quality.overall_score, 2)
            },
            "statistics": {
                "total_messages": len(messages),
                "question_count": len([p for p in qa_pairs if p.get("question")]),
                "answer_count": len([p for p in qa_pairs if p.get("answer")]),
                "avg_answer_length": self._calculate_avg_answer_length(qa_pairs),
                "speaking_time_estimate": len(messages) * 30  # 30 sec per message estimate
            },
            "recommendations": recommendations,
            "gaps": self._identify_gaps(qa_pairs, focus_areas)
        }

    def _extract_qa_pairs(self, messages: List[Dict]) -> List[Dict]:
        """Extract question-answer pairs from messages"""
        pairs = []
        current_question = None

        for msg in messages:
            content = msg.get('content', msg.get('text', ''))
            role = msg.get('role', '').lower()

            # Detect questions (interviewer or ends with ?)
            is_question = role == 'interviewer' or '?' in content

            if is_question:
                # Save previous Q&A pair
                if current_question:
                    pairs.append(current_question)

                # Start new question
                current_question = {
                    'question': content,
                    'answer': '',
                    'speaker': role
                }
            elif current_question:
                # This is an answer
                current_question['answer'] += ' ' + content

        # Save last pair
        if current_question and current_question.get('answer'):
            pairs.append(current_question)

        return pairs

    def _detect_conversation_type(
        self,
        title: str,
        messages: List[Dict],
        qa_pairs: List[Dict]
    ) -> str:
        """Detect the type of conversation"""
        title_lower = title.lower()
        text_sample = ' '.join([m.get('content', m.get('text', '')) for m in messages[:5]]).lower()

        # Try SmartClassifier first if available
        try:
            from modules.ai.smart_classifier import get_classifier, CLASSIFIER_AVAILABLE
            if CLASSIFIER_AVAILABLE:
                classifier = get_classifier()
                if classifier:
                    conv_type, confidence = classifier.classify_conversation_type(title, text_sample)
                    if confidence > 0.5:
                        return conv_type
        except Exception:
            pass  # nosec B110

        # Fallback: keyword-based classification
        scores = {}

        for conv_type, patterns in self.TYPE_PATTERNS.items():
            score = 0.0

            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in title_lower:
                    score += patterns["weight"]
                if keyword in text_sample:
                    score += patterns["weight"] * 0.5

            # Check indicators
            if "multiple_speakers" in patterns["indicators"]:
                speakers = set(m.get('role', '') for m in messages)
                if len(speakers) > 1:
                    score += 0.3

            if "structured_qa" in patterns["indicators"]:
                if len(qa_pairs) >= 3:
                    score += 0.3

            if "company_mentioned" in patterns["indicators"]:
                # Check for company mentions
                companies = ["google", "meta", "amazon", "microsoft", "apple", "netflix"]
                if any(c in text_sample for c in companies):
                    score += 0.4

            scores[conv_type] = score

        # Return highest scoring type
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0.5:
                return best_type

        return "practice_session"  # Default

    def _analyze_content_focus(self, qa_pairs: List[Dict]) -> List[str]:
        """Analyze what the conversation focuses on"""
        focus_areas = []

        all_text = ' '.join([
            p.get('question', '') + ' ' + p.get('answer', '')
            for p in qa_pairs
        ]).lower()

        for category, config in self.CONTENT_CATEGORIES.items():
            keyword_count = sum(
                1 for keyword in config["keywords"] if keyword in all_text
            )

            # Calculate percentage of questions mentioning keywords
            total_questions = len(qa_pairs)
            if total_questions > 0:
                coverage = keyword_count / len(config["keywords"])

                if coverage >= config["threshold"]:
                    focus_areas.append(category)

        return focus_areas if focus_areas else ["general"]

    def _analyze_difficulty_distribution(
        self,
        qa_pairs: List[Dict]
    ) -> Dict[str, int]:
        """Analyze difficulty distribution of questions"""
        difficulties = {"easy": 0, "medium": 0, "hard": 0}

        for pair in qa_pairs:
            question = pair.get('question', '').lower()

            # Detect difficulty from question
            if any(word in question for word in ["hard", "difficult", "complex", "advanced", "optimize"]):
                difficulties["hard"] += 1
            elif any(word in question for word in ["medium", "typical", "standard", "design"]):
                difficulties["medium"] += 1
            else:
                difficulties["easy"] += 1

        return difficulties

    def _detect_star_method(self, qa_pairs: List[Dict]) -> bool:
        """Detect if answers follow STAR method"""
        star_compliant = 0

        for pair in qa_pairs:
            answer = pair.get('answer', '').lower()

            if not answer:
                continue

            # Count STAR components present
            components = 0
            for component, patterns in self.STAR_PATTERNS.items():
                if any(pattern in answer for pattern in patterns):
                    components += 1

            # Consider STAR formatted if 3+ components present
            if components >= 3:
                star_compliant += 1

        # Return True if majority of behavioral answers follow STAR
        behavioral_qa = len([p for p in qa_pairs if "tell me about" in p.get('question', '').lower()])
        if behavioral_qa > 0:
            return star_compliant / behavioral_qa >= 0.5

        return star_compliant >= len(qa_pairs) * 0.3

    def _calculate_quality_metrics(
        self,
        messages: List[Dict],
        qa_pairs: List[Dict]
    ) -> QualityMetrics:
        """Calculate quality metrics"""
        # Completeness: ratio of questions with substantial answers
        complete_answers = sum(
            1 for p in qa_pairs
            if len(p.get('answer', '').split()) >= 20  # At least 20 words
        )
        completeness = complete_answers / max(len(qa_pairs), 1)

        # Technical depth: presence of technical terms
        all_answers = ' '.join([p.get('answer', '') for p in qa_pairs])
        technical_terms = len(re.findall(r'\b(?:api|database|algorithm|function|class|method|variable)\b', all_answers.lower()))
        technical_depth = min(technical_terms / max(len(qa_pairs), 1) / 2, 1.0)

        # Clarity: low filler word ratio
        filler_count = sum(
            all_answers.lower().count(filler)
            for filler in self.filler_words
        )
        word_count = len(all_answers.split())
        filler_ratio = filler_count / max(word_count, 1)
        clarity = max(0, 1 - filler_ratio * 10)  # Penalize fillers

        # Structure: organized paragraphs, numbered lists
        structured_indicators = len(re.findall(r'\b(first|second|third|1\.|2\.|3\.)\b', all_answers.lower()))
        structure = min(structured_indicators / max(len(qa_pairs), 1), 1.0)

        # Overall score (weighted average)
        overall = (
            completeness * 0.3 +
            technical_depth * 0.25 +
            clarity * 0.25 +
            structure * 0.2
        )

        return QualityMetrics(
            completeness=completeness,
            technical_depth=technical_depth,
            clarity_score=clarity,
            structure_score=structure,
            overall_score=overall
        )

    def _determine_quality_tier(self, metrics: QualityMetrics) -> str:
        """Determine quality tier based on metrics"""
        if metrics.overall_score >= 0.8:
            return "excellent"
        elif metrics.overall_score >= 0.6:
            return "good"
        elif metrics.overall_score >= 0.4:
            return "average"
        return "needs_improvement"

    def _calculate_avg_answer_length(self, qa_pairs: List[Dict]) -> int:
        """Calculate average answer length in words"""
        if not qa_pairs:
            return 0

        total_words = sum(
            len(p.get('answer', '').split())
            for p in qa_pairs
        )
        return total_words // len(qa_pairs)

    def _generate_recommendations(
        self,
        qa_pairs: List[Dict],
        focus_areas: List[str],
        quality: QualityMetrics,
        star_formatted: bool
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        # Completeness recommendations
        if quality.completeness < 0.7:
            recommendations.append(
                "Try to provide more complete answers with examples and details"
            )

        # STAR method recommendations
        if not star_formatted:
            recommendations.append(
                "Practice using STAR format (Situation, Task, Action, Result) for behavioral questions"
            )

        # Technical depth recommendations
        if quality.technical_depth < 0.5:
            recommendations.append(
                "Include more technical specifics in your answers"
            )

        # Focus area recommendations
        if "system_design_focus" in focus_areas and quality.technical_depth < 0.7:
            recommendations.append(
                "Study system design fundamentals - trade-offs, scalability, and component selection"
            )

        if "algorithm_heavy" in focus_areas:
            recommendations.append(
                "Practice explaining time/space complexity clearly"
            )

        # Clarity recommendations
        if quality.clarity_score < 0.6:
            recommendations.append(
                "Reduce filler words (um, uh, like) for clearer communication"
            )

        return recommendations if recommendations else ["Keep up the good work!"]

    def _identify_gaps(
        self,
        qa_pairs: List[Dict],
        focus_areas: List[str]
    ) -> List[str]:
        """Identify gaps in interview preparation"""
        gaps = []

        # Check for missing question types
        all_questions = ' '.join([p.get('question', '').lower() for p in qa_pairs])

        if "behavioral" not in focus_areas and "tell me about" not in all_questions:
            gaps.append("behavioral_questions")

        if "system_design" not in focus_areas and "design" not in all_questions:
            gaps.append("system_design")

        if "algorithm" not in focus_areas:
            gaps.append("technical_questions")

        return gaps

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "conversation_id": "unknown",
            "title": "",
            "analysis_timestamp": datetime.now().isoformat(),
            "tags": {
                "type": "unknown",
                "focus_areas": [],
                "difficulty_distribution": {},
                "is_star_formatted": False,
                "quality_tier": "unknown"
            },
            "quality_metrics": {
                "completeness": 0.0,
                "technical_depth": 0.0,
                "clarity_score": 0.0,
                "structure_score": 0.0,
                "overall_score": 0.0
            },
            "statistics": {
                "total_messages": 0,
                "question_count": 0,
                "answer_count": 0,
                "avg_answer_length": 0,
                "speaking_time_estimate": 0
            },
            "recommendations": ["No data to analyze"],
            "gaps": []
        }


# Global instance
analyzer = ConversationAnalyzer()


def analyze_conversation(conversation: Dict) -> Dict:
    """Analyze conversation - convenience function"""
    return analyzer.analyze_conversation(conversation)


def get_conversation_summary(conversation_id: str, conversations: List[Dict]) -> Dict:
    """Get quick summary of a conversation by ID"""
    conv = next((c for c in conversations if c.get("id") == conversation_id), None)
    if conv:
        return analyzer.analyze_conversation(conv)
    return {"error": "Conversation not found"}


def batch_analyze_conversations(conversations: List[Dict]) -> List[Dict]:
    """Analyze multiple conversations and return summaries"""
    return [analyzer.analyze_conversation(c) for c in conversations]
