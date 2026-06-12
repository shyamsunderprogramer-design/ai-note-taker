"""
Meeting Agent — LLM-powered real-time meeting notes.

Extracts action items, decisions, and open questions during meetings.
Runs on every transcript segment (not just questions), with accumulated notes
to prevent duplicate extraction.
"""

import re
import logging
from typing import List, Dict, Any

from modules.agents.base import (
    BaseAgent, AgentType, AgentSuggestion, AgentContext,
    TranscriptSegment,
)
from modules.agents.context_builder import query_document_rag, extract_entities
from modules.agents.prompts import MEETING_AGENT_PROMPT
from modules.agents.session import AgentSessionManager

logger = logging.getLogger("agents.meeting")


class MeetingAgent(BaseAgent):
    """LLM-powered meeting assistant that extracts action items,
    decisions, and open questions in real-time."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.MEETING

    @property
    def display_name(self) -> str:
        return "Meeting Assistant"

    @property
    def description(self) -> str:
        return "Automatically captures action items, decisions, and open questions during your meeting"

    @property
    def cooldown_seconds(self) -> float:
        return 15.0  # Longer cooldown — meeting notes don't need to be instant

    @property
    def required_data_sources(self) -> List[str]:
        return ["entity_extraction"]

    def should_activate(self, session: Any, segment: TranscriptSegment) -> bool:
        """Activate on every segment from any speaker.
        Meeting notes should capture everything, not just questions."""
        # Skip very short segments (likely noise)
        if len(segment.text.strip()) < 15:
            return False
        return True

    def build_context(self, session: Any) -> AgentContext:
        """Assemble context for meeting note extraction."""
        from agents.session import session_manager

        # Transcript window (last 10 segments — ~60 seconds of conversation)
        transcript_window = session_manager.format_transcript_window(session, last_n=10)

        # Accumulated notes from previous runs
        agent_state = session_manager.get_agent_state(session, self.agent_type.value)
        accumulated_notes = agent_state.get("accumulated_notes", "")

        # Session title
        company = session.get("company", "")
        role = session.get("role", "")
        session_title = f"Meeting"
        if company:
            session_title += f" at {company}"
        if role:
            session_title += f" — {role}"

        # Document RAG (if meeting relates to uploaded docs)
        document_rag_results = []
        # Use the full transcript window as the query for document context
        if transcript_window and len(transcript_window) > 50:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    # Use last segment text as query
                    buffer = session.get("transcript_buffer", [])
                    last_text = buffer[-1].get("text", "") if buffer else ""
                    if last_text:
                        document_rag_results = loop.run_until_complete(
                            query_document_rag(last_text, top_k=2)
                        )
            except Exception:
                pass  # nosec B110

        return AgentContext(
            transcript_window=transcript_window,
            accumulated_notes=accumulated_notes,
            document_rag_results=document_rag_results,
            session_metadata={
                "session_title": session_title,
            },
        )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the meeting notes prompt."""
        session_title = context.session_metadata.get("session_title", "Meeting")

        return MEETING_AGENT_PROMPT.format(
            session_title=session_title,
            transcript_window=context.transcript_window or "(no conversation yet)",
            accumulated_notes=context.accumulated_notes or "(none yet — this is the start)",
        )

    def parse_suggestions(self, raw_response: str, context: AgentContext) -> List[AgentSuggestion]:
        """Parse meeting notes into structured suggestions.

        Each ACTION/DECISION/QUESTION line becomes one suggestion.
        """
        suggestions = []

        # Check for no-new-items signal
        if "NO_NEW_ITEMS" in raw_response.upper():
            return suggestions

        lines = raw_response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.upper().startswith("ACTION:"):
                content = line[7:].strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="action_item",
                        content=content,
                        confidence=0.85,
                        metadata={"type": "action_item"},
                    ))

            elif line.upper().startswith("DECISION:"):
                content = line[9:].strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="decision",
                        content=content,
                        confidence=0.90,
                        metadata={"type": "decision"},
                    ))

            elif line.upper().startswith("QUESTION:"):
                content = line[9:].strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="question",
                        content=content,
                        confidence=0.80,
                        metadata={"type": "open_question"},
                    ))

        # Fallback: if no structured lines found, try to extract useful content
        if not suggestions and raw_response.strip() and "NO_NEW_ITEMS" not in raw_response.upper():
            suggestions.append(AgentSuggestion(
                id=self._new_suggestion_id(),
                agent_type=self.agent_type.value,
                category="action_item",
                content=raw_response.strip()[:500],
                confidence=0.60,
                metadata={"type": "note", "parsed_fallback": True},
            ))

        return suggestions

    def update_accumulated_notes(self, session: Any, new_items: List[AgentSuggestion]) -> None:
        """Append new items to the accumulated notes to prevent duplicates on next run."""
        from agents.session import session_manager

        agent_state = session_manager.get_agent_state(session, self.agent_type.value)
        current_notes = agent_state.get("accumulated_notes", "")

        new_lines = []
        for item in new_items:
            prefix = {
                "action_item": "ACTION",
                "decision": "DECISION",
                "question": "QUESTION",
            }.get(item.category, "NOTE")
            new_lines.append(f"{prefix}: {item.content}")

        if new_lines:
            updated = current_notes + "\n" + "\n".join(new_lines) if current_notes else "\n".join(new_lines)
            # Keep notes under 2000 chars to avoid prompt bloat
            if len(updated) > 2000:
                updated = updated[-2000:]
            session_manager.update_agent_state(
                session, self.agent_type.value,
                {"accumulated_notes": updated}
            )