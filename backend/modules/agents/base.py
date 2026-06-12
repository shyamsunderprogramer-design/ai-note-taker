"""
Base classes for the AI Agent framework.

Defines the contract every agent must implement:
  - build_context(): assemble rich context from data sources
  - build_prompt(): construct LLM prompt from context
  - parse_suggestions(): parse structured output into AgentSuggestion objects
  - generate_suggestions(): stream via route_ai_stream()
  - should_activate(): decide if agent should run for a given segment
"""

import re
import uuid
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("agents.base")


class AgentType(str, Enum):
    MEETING = "meeting"
    SALES_COACH = "sales_coach"
    INTERVIEW_COACH = "interview_coach"


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SUGGESTING = "suggesting"
    ERROR = "error"


@dataclass
class TranscriptSegment:
    text: str
    speaker: str  # "user", "interviewer", "other"
    timestamp: float
    is_question: bool = False


@dataclass
class AgentSuggestion:
    id: str
    agent_type: str  # AgentType value
    category: str  # e.g. "action_item", "objection", "rebuttal", "talking_point", "technical", "behavioral"
    content: str
    confidence: float
    metadata: Dict = field(default_factory=dict)
    # metadata can include: source_docs, graph_matches, entities, hotkey, bant_update

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "category": self.category,
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class AgentContext:
    """Assembled context that gets injected into the LLM prompt."""
    transcript_window: str = ""
    entities: Dict = field(default_factory=dict)
    cognitive_graph_results: List[Dict] = field(default_factory=list)
    document_rag_results: List[Dict] = field(default_factory=list)
    user_profile: Dict = field(default_factory=dict)
    session_metadata: Dict = field(default_factory=dict)
    company_insights: Dict = field(default_factory=dict)
    skill_progression: List[Dict] = field(default_factory=list)
    current_question: str = ""
    accumulated_notes: str = ""  # For Meeting Agent
    bant_status: Dict = field(default_factory=dict)  # For Sales Coach


# Question detection patterns
_QUESTION_INDICATORS = (
    "?", "can you", "how would", "what is", "explain",
    "tell me", "describe", "why", "when", "where",
    "could you", "would you", "what are", "how do",
    "what's", "how's", "share", "walk me", "help me understand"
)


def is_question(text: str) -> bool:
    """Detect if a transcript segment is a question."""
    lower = text.lower().strip()
    if not lower:
        return False
    if lower.endswith("?"):
        return True
    return any(ind in lower for ind in _QUESTION_INDICATORS)


class BaseAgent(ABC):
    """Abstract base class for all AI agents."""

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """The type of this agent."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in UI."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this agent does."""
        ...

    @property
    @abstractmethod
    def cooldown_seconds(self) -> float:
        """Minimum seconds between activations."""
        ...

    @property
    @abstractmethod
    def required_data_sources(self) -> List[str]:
        """Data source keys this agent needs.
        Options: 'cognitive_graph', 'document_rag', 'entity_extraction',
                 'user_profile', 'company_insights', 'skill_progression'
        """
        ...

    @abstractmethod
    def build_context(self, session: Any) -> AgentContext:
        """Assemble the rich context object from available data sources.
        Must degrade gracefully if any source is unavailable."""
        ...

    @abstractmethod
    def build_prompt(self, context: AgentContext) -> str:
        """Build the full LLM prompt from the assembled context."""
        ...

    @abstractmethod
    def parse_suggestions(self, raw_response: str, context: AgentContext) -> List[AgentSuggestion]:
        """Parse the LLM's raw text output into structured AgentSuggestion objects."""
        ...

    def should_activate(self, session: Any, segment: TranscriptSegment) -> bool:
        """Decide if this agent should run for the given segment.
        Default: activate on questions from non-user speakers.
        Agents should override for custom logic."""
        return segment.speaker != "user" and segment.is_question

    def is_in_cooldown(self, session: Any) -> bool:
        """Check if this agent is in its cooldown period."""
        agent_states = getattr(session, 'agent_states', {}) or {}
        my_state = agent_states.get(self.agent_type.value, {})
        last_time = my_state.get("last_suggestion_time", 0)
        return (time.time() - last_time) < self.cooldown_seconds

    def set_cooldown(self, session: Any) -> None:
        """Mark that this agent just produced a suggestion."""
        agent_states = getattr(session, 'agent_states', {}) or {}
        if self.agent_type.value not in agent_states:
            agent_states[self.agent_type.value] = {}
        agent_states[self.agent_type.value]["last_suggestion_time"] = time.time()
        session.agent_states = agent_states

    async def generate_suggestions(self, session: Any) -> Any:
        """Stream suggestions via route_ai_stream. Yields SSE event strings.
        """
        context = self.build_context(session)
        prompt = self.build_prompt(context)

        try:
            from ai_router import route_ai_stream
        except ImportError:
            try:
                from modules.ai.ai_router import route_ai_stream
            except ImportError:
                from backend.modules.ai.ai_router import route_ai_stream

        provider = getattr(session, 'config', {}).get("provider", "ollama")

        async for event in route_ai_stream(
            prompt,
            mode="interview",
            style="concise",
            provider=provider,
        ):
            yield event, context

    def _new_suggestion_id(self) -> str:
        return f"{self.agent_type.value}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _parse_confidence(text: str) -> float:
        """Extract confidence from text like 'confidence: 0.85'."""
        match = re.search(r'confidence[:\s]+(0?\.\d+)', text)
        if match:
            return min(1.0, max(0.0, float(match.group(1))))
        return 0.75  # default confidence

    @staticmethod
    def _parse_category(text: str) -> str:
        """Extract category from structured LLM output."""
        categories = [
            "technical", "behavioral", "clarification", "strategic",
            "stalling", "action_item", "decision", "question",
            "objection", "rebuttal", "talking_point",
        ]
        lower = text.lower()
        for cat in categories:
            if cat in lower:
                return cat
        return "general"