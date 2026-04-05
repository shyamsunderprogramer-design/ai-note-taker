"""
realtime_suggestions.py - Real-Time Suggestion Engine

Provides contextual hints during live interviews by:
1. Listening to transcript segments
2. Detecting interviewer questions
3. Querying cognitive graph for similar past Q&A
4. Showing suggestion cards with confidence scores

Phase 2 Task #28
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
from collections import deque

logger = logging.getLogger("realtime_suggestions")

# Import cognitive graph
try:
    from cognitive_graph import cognitive_graph, query_graph
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False
    logger.warning("[RealtimeSuggestions] Cognitive graph not available")


@dataclass
class Suggestion:
    """A single suggestion for the user"""
    id: str
    type: str  # "similar_question", "topic_hint", "company_pattern", "skill_reminder"
    content: str
    context: Dict  # Full context from cognitive graph
    confidence: float
    relevance_score: float
    timestamp: datetime
    source: str  # Where this suggestion came from


@dataclass
class TranscriptSegment:
    """A segment of transcript audio"""
    text: str
    speaker: str  # "user" or "interviewer"
    timestamp: float
    confidence: float
    is_question: bool = False


class RealtimeSuggestionEngine:
    """
    Real-time suggestion engine for interview assistance.

    Usage:
        engine = RealtimeSuggestionEngine()
        suggestion = engine.process_segment("Tell me about React hooks", "interviewer")
        if suggestion:
            display_to_user(suggestion)
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        buffer_size: int = 5,
        cooldown_seconds: float = 10.0
    ):
        """
        Args:
            min_confidence: Minimum confidence to show suggestion (0.0-1.0)
            buffer_size: Number of segments to keep in memory
            cooldown_seconds: Minimum time between suggestions
        """
        self.min_confidence = min_confidence
        self.cooldown_seconds = cooldown_seconds
        self.segment_buffer: deque = deque(maxlen=buffer_size)
        self.last_suggestion_time: Optional[float] = None
        self.suggestion_history: List[Suggestion] = []
        self._question_pattern = re.compile(r'\?$|^(what|how|why|when|where|who|can|could|would|tell me|explain|describe)', re.IGNORECASE)

    def is_question(self, text: str) -> bool:
        """Detect if text is a question"""
        # Check for question mark or question words
        if self._question_pattern.search(text.strip()):
            return True

        # Check for common interview question patterns
        interview_patterns = [
            r'implement',
            r'design',
            r'optimize',
            r'compare',
            r'difference between',
            r'how would you',
            r'what is',
            r'explain',
        ]

        text_lower = text.lower()
        for pattern in interview_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def process_segment(
        self,
        text: str,
        speaker: str,
        timestamp: Optional[float] = None
    ) -> Optional[Suggestion]:
        """
        Process a new transcript segment and return suggestion if relevant.

        Args:
            text: The transcript text
            speaker: "user" or "interviewer"
            timestamp: Unix timestamp (optional, defaults to now)

        Returns:
            Suggestion object or None if no suggestion needed
        """
        if timestamp is None:
            timestamp = datetime.now().timestamp()

        # Create segment
        segment = TranscriptSegment(
            text=text,
            speaker=speaker,
            timestamp=timestamp,
            confidence=1.0,
            is_question=self.is_question(text)
        )

        # Add to buffer
        self.segment_buffer.append(segment)

        # Only process interviewer questions
        if speaker != "interviewer" or not segment.is_question:
            return None

        # Check cooldown
        if self.last_suggestion_time and \
           (timestamp - self.last_suggestion_time) < self.cooldown_seconds:
            return None

        # Generate suggestion
        suggestion = self._generate_suggestion(segment)

        if suggestion and suggestion.confidence >= self.min_confidence:
            self.last_suggestion_time = timestamp
            self.suggestion_history.append(suggestion)
            return suggestion

        return None

    def _generate_suggestion(self, segment: TranscriptSegment) -> Optional[Suggestion]:
        """Generate a suggestion based on the question"""
        if not COGNITIVE_GRAPH_AVAILABLE:
            return None

        # Query cognitive graph for similar questions
        similar = query_graph(segment.text)

        if not similar:
            # Try with extracted keywords
            keywords = self._extract_keywords(segment.text)
            if keywords:
                similar = query_graph(" ".join(keywords))

        if not similar:
            return None

        # Get top match
        top_match = similar[0]

        # Calculate confidence
        confidence = self._calculate_confidence(segment.text, top_match)

        # Create suggestion
        suggestion = Suggestion(
            id=f"sugg-{len(self.suggestion_history)}",
            type="similar_question",
            content=self._format_suggestion(top_match),
            context=top_match,
            confidence=confidence,
            relevance_score=top_match.get("relevance", 0.5),
            timestamp=datetime.now(),
            source="cognitive_graph"
        )

        return suggestion

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key technical terms from question"""
        # Technical keywords to look for
        tech_keywords = {
            "react", "javascript", "python", "algorithm", "database",
            "api", "system design", "microservices", "cache", "redis",
            "load balancer", "distributed", "scale", "performance",
            "optimization", "complexity", "tree", "graph", "array",
            "kubernetes", "docker", "aws", "cloud", "serverless"
        }

        text_lower = text.lower()
        found = []

        for keyword in tech_keywords:
            if keyword in text_lower:
                found.append(keyword)

        return found

    def _calculate_confidence(
        self,
        query: str,
        match: Dict
    ) -> float:
        """Calculate confidence score for suggestion"""
        confidence = 0.5

        # Base confidence on graph relevance
        relevance = match.get("relevance", 0)
        confidence += relevance * 0.3

        # Boost if same category
        if match.get("category"):
            confidence += 0.1

        # Boost if company matches
        if match.get("company"):
            confidence += 0.1

        # Penalize if query is too short
        if len(query) < 20:
            confidence -= 0.2

        return min(max(confidence, 0.0), 1.0)

    def _format_suggestion(self, match: Dict) -> str:
        """Format the suggestion content for display"""
        question = match.get("question", "")
        answer = match.get("answer", "")
        company = match.get("company")
        topics = match.get("topics", [])

        # Truncate for display
        question_short = question[:100] + "..." if len(question) > 100 else question

        content = f"You've seen a similar question before:\n\n**{question_short}**"

        if company:
            content += f"\n\nAsked by: {company}"

        if topics:
            content += f"\nTopics: {', '.join(topics[:3])}"

        if answer:
            answer_preview = answer[:150] + "..." if len(answer) > 150 else answer
            content += f"\n\nYour previous answer:\n{answer_preview}"

        return content

    def get_suggestion_history(
        self,
        limit: int = 50
    ) -> List[Suggestion]:
        """Get history of suggestions shown"""
        return self.suggestion_history[-limit:]

    def clear_buffer(self):
        """Clear the transcript buffer"""
        self.segment_buffer.clear()
        self.last_suggestion_time = None

    def set_min_confidence(self, confidence: float):
        """Update minimum confidence threshold"""
        self.min_confidence = max(0.0, min(1.0, confidence))


class VoiceCommandProcessor:
    """Process voice commands during interview"""

    COMMAND_PATTERNS = {
        "search": [
            r"what did i say about (.+)",
            r"remind me about (.+)",
            r"search for (.+)",
            r"find (.+) in my history"
        ],
        "suggest": [
            r"give me a hint",
            r"what should i say",
            r"help me with this"
        ],
        "stats": [
            r"how many (.+) questions",
            r"show my (.+) progress"
        ]
    }

    def __init__(self, suggestion_engine: RealtimeSuggestionEngine):
        self.engine = suggestion_engine

    def process_command(self, text: str) -> Optional[Dict]:
        """
        Process voice command and return action.

        Returns:
            Dict with action type and data, or None if not a command
        """
        text_lower = text.lower().strip()

        # Check for search commands
        for pattern in self.COMMAND_PATTERNS["search"]:
            match = re.search(pattern, text_lower)
            if match:
                query = match.group(1).strip()
                results = query_graph(query)
                return {
                    "action": "search_results",
                    "query": query,
                    "results": results
                }

        # Check for suggestion request
        for pattern in self.COMMAND_PATTERNS["suggest"]:
            if re.search(pattern, text_lower):
                # Get last interviewer question from buffer
                for seg in reversed(self.engine.segment_buffer):
                    if seg.speaker == "interviewer" and seg.is_question:
                        suggestion = self.engine._generate_suggestion(seg)
                        if suggestion:
                            return {
                                "action": "suggestion",
                                "suggestion": suggestion
                            }
                return {
                    "action": "error",
                    "message": "No recent question found to suggest for"
                }

        return None


# Global instance
realtime_engine = RealtimeSuggestionEngine()
voice_processor = VoiceCommandProcessor(realtime_engine)


# Convenience functions
def process_transcript_segment(text: str, speaker: str) -> Optional[Suggestion]:
    """Process a transcript segment - convenience function"""
    return realtime_engine.process_segment(text, speaker)


def process_voice_command(text: str) -> Optional[Dict]:
    """Process voice command - convenience function"""
    return voice_processor.process_command(text)


def set_suggestion_confidence(confidence: float):
    """Set minimum confidence threshold"""
    realtime_engine.set_min_confidence(confidence)
