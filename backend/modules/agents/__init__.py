"""
AI Agents Module — Unified LLM-powered agent framework.

Replaces template-matching Shadow Agent with real AI agents that use
route_ai_stream() for contextual, personalized suggestions.

Agent Types:
  - InterviewCoachAgent: Real-time interview assistance with LLM + cognitive graph + RAG
  - MeetingAgent: Action items, decisions, open questions extraction
  - SalesCoachAgent: Objection detection, rebuttals, BANT/MEDDIC tracking

Supporting modules:
  - cache: Context caching to avoid redundant data source queries
  - learning: Self-learning from user feedback (accept/dismiss)
  - ingestion: Interview data ingestion pipeline (Q&A + PDF → graph + RAG)
  - vibevoice_diarizer: Speaker diarization integration (in voice module)
"""

from agents.base import AgentType, AgentState, AgentSuggestion, AgentContext, BaseAgent, TranscriptSegment
from agents.orchestrator import AgentOrchestrator
from agents.session import AgentSessionManager

__all__ = [
    "AgentType", "AgentState", "AgentSuggestion", "AgentContext",
    "BaseAgent", "TranscriptSegment",
    "AgentOrchestrator", "AgentSessionManager",
]