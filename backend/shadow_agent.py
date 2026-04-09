"""
Shadow Interview Agent
Autonomous agent that operates in background during interviews
Provides real-time suggestions and response generation
"""

import json
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SUGGESTING = "suggesting"


@dataclass
class InterviewContext:
    company: str = ""
    role: str = ""
    interviewer_name: str = ""
    stage: str = ""  # phone_screen, technical, behavioral, final
    questions_asked: List[str] = field(default_factory=list)
    current_question: str = ""
    user_responses: List[str] = field(default_factory=list)


@dataclass
class Suggestion:
    id: str
    text: str
    confidence: float
    source: str  # context, pattern, knowledge_graph
    category: str  # technical, behavioral, clarification
    hotkey: str


class ShadowInterviewAgent:
    """
    Shadow agent that provides interview assistance.

    Features:
    - Background listening for questions
    - Real-time response generation
    - Hotkey-based insertion (Ctrl+1, Ctrl+2, Ctrl+3)
    - Context-aware suggestions
    """

    def __init__(self):
        self.state = AgentState.IDLE
        self.context = InterviewContext()
        self.suggestions: List[Suggestion] = []
        self.suggestion_history: List[Dict] = []
        self.last_activity = time.time()
        self.config = {
            "auto_generate": True,
            "suggestion_count": 3,
            "min_confidence": 0.6,
            "hotkeys": ["Ctrl+1", "Ctrl+2", "Ctrl+3"],
        }

    def start_session(self, company: str, role: str, stage: str = "") -> Dict:
        """Start a new interview session"""
        self.state = AgentState.LISTENING
        self.context = InterviewContext(
            company=company,
            role=role,
            stage=stage
        )
        self.suggestions = []
        self.last_activity = time.time()

        return {
            "status": "started",
            "session_id": f"shadow_{int(time.time())}",
            "company": company,
            "role": role,
            "message": "Shadow agent is listening. Press Ctrl+~ to toggle overlay."
        }

    def process_transcript(self, text: str, speaker: str) -> Optional[Dict]:
        """
        Process incoming transcript.

        Detects questions and generates suggestions.
        """
        self.last_activity = time.time()

        # Detect if interviewer is asking a question
        if speaker == "interviewer" or speaker == "other":
            question_indicators = [
                "?", "can you", "how would", "what is", "explain",
                "tell me", "describe", "why", "when", "where"
            ]

            is_question = any(ind in text.lower() for ind in question_indicators)

            if is_question:
                self.context.current_question = text
                self.context.questions_asked.append(text)

                # Generate suggestions
                if self.config["auto_generate"]:
                    self.state = AgentState.THINKING
                    self.suggestions = self._generate_suggestions(text)
                    self.state = AgentState.SUGGESTING

                    return {
                        "detected": "question",
                        "question": text,
                        "suggestions": [
                            {
                                "id": s.id,
                                "text": s.text,
                                "confidence": s.confidence,
                                "hotkey": s.hotkey,
                                "category": s.category
                            }
                            for s in self.suggestions
                        ],
                        "hotkeys": self.config["hotkeys"][:len(self.suggestions)]
                    }

        # Track user responses
        elif speaker == "user":
            self.context.user_responses.append(text)

        return None

    def _generate_suggestions(self, question: str) -> List[Suggestion]:
        """
        Generate response suggestions based on question.

        In full implementation, this would:
        1. Query cognitive graph for similar past questions
        2. Use predictive engine for company-specific patterns
        3. Generate responses using AI model
        """
        suggestions = []

        # Detect question type
        q_lower = question.lower()

        if any(kw in q_lower for kw in ["system design", "architecture", "scale"]):
            # System design suggestion
            suggestions.append(Suggestion(
                id="s1",
                text="I'd start by clarifying requirements: functional needs, scale (DAU, QPS), and constraints. Then outline the high-level components before diving into details.",
                confidence=0.92,
                source="pattern",
                category="technical",
                hotkey="Ctrl+1"
            ))
            suggestions.append(Suggestion(
                id="s2",
                text="Key considerations: data model, API design, service boundaries, database choice, caching strategy, and monitoring.",
                confidence=0.85,
                source="knowledge",
                category="technical",
                hotkey="Ctrl+2"
            ))

        elif any(kw in q_lower for kw in ["tell me about yourself", "background", "experience"]):
            # Behavioral - intro
            suggestions.append(Suggestion(
                id="s1",
                text=f"I'm a {self.context.role.replace('_', ' ')} with experience in [key technologies]. Most recently at [company], I [impact statement with metrics].",
                confidence=0.88,
                source="template",
                category="behavioral",
                hotkey="Ctrl+1"
            ))

        elif any(kw in q_lower for kw in ["challenge", "difficult", "problem"]):
            # Behavioral - challenges
            suggestions.append(Suggestion(
                id="s1",
                text="Using the STAR method: Situation was [context], Task was [my responsibility], Action I took was [steps], Result was [measurable outcome].",
                confidence=0.90,
                source="framework",
                category="behavioral",
                hotkey="Ctrl+1"
            ))

        elif any(kw in q_lower for kw in ["coding", "implement", "write a function", "algorithm"]):
            # Coding question
            suggestions.append(Suggestion(
                id="s1",
                text="First, let me understand the requirements. What's the input size? Are there any constraints on space or time complexity?",
                confidence=0.87,
                source="strategy",
                category="clarification",
                hotkey="Ctrl+1"
            ))
            suggestions.append(Suggestion(
                id="s2",
                text="I'll approach this by [explain approach]. Time complexity would be O(n) and space is O(1).",
                confidence=0.82,
                source="template",
                category="technical",
                hotkey="Ctrl+2"
            ))

        else:
            # Generic suggestions
            suggestions.append(Suggestion(
                id="s1",
                text="That's an interesting question. Let me think through this step by step...",
                confidence=0.70,
                source="generic",
                category="stalling",
                hotkey="Ctrl+1"
            ))
            suggestions.append(Suggestion(
                id="s2",
                text="From my experience, I'd approach this by [share relevant experience].",
                confidence=0.65,
                source="generic",
                category="behavioral",
                hotkey="Ctrl+2"
            ))

        # Filter by confidence
        suggestions = [s for s in suggestions if s.confidence >= self.config["min_confidence"]]

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        return suggestions[:self.config["suggestion_count"]]

    def get_suggestions(self) -> List[Dict]:
        """Get current suggestions"""
        return [
            {
                "id": s.id,
                "text": s.text,
                "confidence": s.confidence,
                "hotkey": s.hotkey,
                "category": s.category
            }
            for s in self.suggestions
        ]

    def accept_suggestion(self, suggestion_id: str) -> Optional[str]:
        """Mark suggestion as accepted (user used it)"""
        for s in self.suggestions:
            if s.id == suggestion_id:
                self.suggestion_history.append({
                    "suggestion": s.text,
                    "question": self.context.current_question,
                    "timestamp": time.time(),
                    "accepted": True
                })
                return s.text
        return None

    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        return {
            "state": self.state.value,
            "questions_heard": len(self.context.questions_asked),
            "suggestions_generated": len(self.suggestion_history),
            "suggestions_accepted": len([s for s in self.suggestion_history if s.get("accepted")]),
            "session_duration_minutes": (time.time() - self.last_activity) / 60
        }

    def clear_suggestions(self):
        """Clear current suggestions"""
        self.suggestions = []
        self.state = AgentState.LISTENING

    def end_session(self) -> Dict:
        """End interview session"""
        stats = self.get_session_stats()
        self.state = AgentState.IDLE
        self.context = InterviewContext()
        self.suggestions = []

        return {
            "status": "ended",
            "stats": stats
        }

    def update_config(self, **kwargs) -> Dict:
        """Update agent configuration"""
        self.config.update(kwargs)
        return self.config


# Global agent instance
shadow_agent = ShadowInterviewAgent()


# API convenience functions
def start_shadow_session(company: str, role: str, stage: str = "") -> Dict:
    return shadow_agent.start_session(company, role, stage)


def process_transcript_segment(text: str, speaker: str) -> Optional[Dict]:
    return shadow_agent.process_transcript(text, speaker)


def get_shadow_suggestions() -> List[Dict]:
    return shadow_agent.get_suggestions()


def accept_suggestion_by_id(suggestion_id: str) -> Optional[str]:
    return shadow_agent.accept_suggestion(suggestion_id)


def end_shadow_session() -> Dict:
    return shadow_agent.end_session()


def get_shadow_stats() -> Dict:
    return shadow_agent.get_session_stats()
