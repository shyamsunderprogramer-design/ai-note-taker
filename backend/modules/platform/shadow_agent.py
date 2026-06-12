"""
Shadow Interview Agent
Autonomous agent that operates in background during interviews
Provides real-time suggestions and response generation
"""

import json
import re
import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("shadow_agent")

# Try importing AI router for LLM-powered suggestions
try:
    from ai_router import route_ai_stream
    HAS_AI_ROUTER = True
except ImportError:
    try:
        from modules.ai.ai_router import route_ai_stream
        HAS_AI_ROUTER = True
    except ImportError:
        HAS_AI_ROUTER = False


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

    async def process_transcript(self, text: str, speaker: str) -> Optional[Dict]:
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
                    self.suggestions = await self._generate_suggestions(text)
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

    async def _generate_suggestions(self, question: str) -> List[Suggestion]:
        """Generate response suggestions using LLM when available, fallback to patterns."""
        # Try LLM-powered generation first
        if HAS_AI_ROUTER:
            llm_suggestions = await self._generate_llm_suggestions(question)
            if llm_suggestions:
                return llm_suggestions

        # Fallback: pattern-based suggestions
        return self._generate_pattern_suggestions(question)

    async def _generate_llm_suggestions(self, question: str) -> List[Suggestion]:
        """Use LLM to generate contextual interview suggestions."""
        try:
            role = self.context.role.replace("_", " ") or "software engineer"
            company = self.context.company or "the company"
            prompt = (
                f"You are an interview coach helping a candidate interviewing for {role} at {company}.\n"
                f"The interviewer just asked: \"{question}\"\n\n"
                f"Provide 3 concise response suggestions. Format each as:\n"
                f"[N] (confidence: 0.XX) category: suggestion text\n\n"
                f"Categories: technical, behavioral, clarification, strategic, stalling\n"
                f"Keep each suggestion to 1-2 sentences. Be specific to the question."
            )

            full_response = ""
            async for event in route_ai_stream(prompt, mode="interview", style="concise"):
                if "event: chunk" in event:
                    try:
                        data_line = [l for l in event.split("\n") if l.startswith("data:")]
                        if data_line:
                            data = json.loads(data_line[0][5:])
                            full_response += data.get("content", "")
                    except (json.JSONDecodeError, IndexError):
                        pass

            # Parse structured output
            suggestions = []
            pattern = r'\[(\d+)\]\s*\(confidence:\s*(0?\.\d+)\)\s*(\w+):\s*(.+)'

            for match in re.finditer(pattern, full_response):
                num, conf_str, category, text = match.groups()
                suggestions.append(Suggestion(
                    id=f"s{num}",
                    text=text.strip(),
                    confidence=min(1.0, max(0.0, float(conf_str))),
                    source="llm",
                    category=category if category in ("technical", "behavioral", "clarification", "strategic", "stalling") else "technical",
                    hotkey=f"Ctrl+{num}"
                ))

            # Fallback: treat each non-empty line as a suggestion
            if not suggestions:
                lines = [l.strip().lstrip("0123456789.-) ") for l in full_response.strip().split("\n") if l.strip()]
                for i, line in enumerate(lines[:3], 1):
                    clean = re.sub(r'^\[[\d]+\]\s*', '', line)
                    if clean:
                        suggestions.append(Suggestion(
                            id=f"s{i}",
                            text=clean,
                            confidence=0.75,
                            source="llm",
                            category=self._classify_question(question),
                            hotkey=f"Ctrl+{i}"
                        ))

            return [s for s in suggestions if s.confidence >= self.config["min_confidence"]]

        except Exception as e:
            logger.warning("[ShadowAgent] LLM generation failed: %s", str(e))
            return []

    def _classify_question(self, question: str) -> str:
        """Classify question type for categorization."""
        q = question.lower()
        if any(kw in q for kw in ["system design", "architecture", "scale", "coding", "implement", "algorithm"]):
            return "technical"
        if any(kw in q for kw in ["tell me", "background", "challenge", "conflict", "leadership"]):
            return "behavioral"
        if any(kw in q for kw in ["can you clarify", "what do you mean", "specifically"]):
            return "clarification"
        return "strategic"

    def _generate_pattern_suggestions(self, question: str) -> List[Suggestion]:
        """Fallback: pattern-based suggestion generation."""
        suggestions = []
        q_lower = question.lower()

        if any(kw in q_lower for kw in ["system design", "architecture", "scale"]):
            suggestions.append(Suggestion(id="s1", text="I'd start by clarifying requirements: functional needs, scale (DAU, QPS), and constraints. Then outline the high-level components before diving into details.", confidence=0.92, source="pattern", category="technical", hotkey="Ctrl+1"))
            suggestions.append(Suggestion(id="s2", text="Key considerations: data model, API design, service boundaries, database choice, caching strategy, and monitoring.", confidence=0.85, source="knowledge", category="technical", hotkey="Ctrl+2"))
        elif any(kw in q_lower for kw in ["tell me about yourself", "background", "experience"]):
            suggestions.append(Suggestion(id="s1", text=f"I'm a {self.context.role.replace('_', ' ')} with experience in [key technologies]. Most recently at [company], I [impact statement with metrics].", confidence=0.88, source="template", category="behavioral", hotkey="Ctrl+1"))
        elif any(kw in q_lower for kw in ["challenge", "difficult", "problem"]):
            suggestions.append(Suggestion(id="s1", text="Using the STAR method: Situation was [context], Task was [my responsibility], Action I took was [steps], Result was [measurable outcome].", confidence=0.90, source="framework", category="behavioral", hotkey="Ctrl+1"))
        elif any(kw in q_lower for kw in ["coding", "implement", "write a function", "algorithm"]):
            suggestions.append(Suggestion(id="s1", text="First, let me understand the requirements. What's the input size? Are there any constraints on space or time complexity?", confidence=0.87, source="strategy", category="clarification", hotkey="Ctrl+1"))
            suggestions.append(Suggestion(id="s2", text="I'll approach this by [explain approach]. Time complexity would be O(n) and space is O(1).", confidence=0.82, source="template", category="technical", hotkey="Ctrl+2"))
        else:
            suggestions.append(Suggestion(id="s1", text="That's an interesting question. Let me think through this step by step...", confidence=0.70, source="generic", category="stalling", hotkey="Ctrl+1"))
            suggestions.append(Suggestion(id="s2", text="From my experience, I'd approach this by [share relevant experience].", confidence=0.65, source="generic", category="behavioral", hotkey="Ctrl+2"))

        suggestions = [s for s in suggestions if s.confidence >= self.config["min_confidence"]]
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


async def process_transcript_segment(text: str, speaker: str) -> Optional[Dict]:
    return await shadow_agent.process_transcript(text, speaker)


def get_shadow_suggestions() -> List[Dict]:
    return shadow_agent.get_suggestions()


def accept_suggestion_by_id(suggestion_id: str) -> Optional[str]:
    return shadow_agent.accept_suggestion(suggestion_id)


def end_shadow_session() -> Dict:
    return shadow_agent.end_session()


def get_shadow_stats() -> Dict:
    return shadow_agent.get_session_stats()
