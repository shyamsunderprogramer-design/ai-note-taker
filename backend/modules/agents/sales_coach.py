"""
Sales Coach Agent — LLM-powered sales call assistance.

Detects objections, suggests rebuttals, and tracks BANT/MEDDIC qualification
during live sales calls. Inspired by Cluely (300ms latency), Fireflies Live Assist,
and Fathom AI Scorecards.
"""

import re
import logging
from typing import List, Dict, Any

from modules.agents.base import (
    BaseAgent, AgentType, AgentSuggestion, AgentContext,
    TranscriptSegment,
)
from modules.agents.context_builder import query_document_rag, extract_entities
from modules.agents.prompts import SALES_COACH_PROMPT, SALES_COACH_PROMPT_MINIMAL
from modules.agents.session import AgentSessionManager

logger = logging.getLogger("agents.sales_coach")


class SalesCoachAgent(BaseAgent):
    """LLM-powered sales coach that detects objections, suggests rebuttals,
    and tracks BANT/MEDDIC qualification during sales calls."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SALES_COACH

    @property
    def display_name(self) -> str:
        return "Sales Coach"

    @property
    def description(self) -> str:
        return "Detects objections, suggests rebuttals, and tracks BANT/MEDDIC qualification on sales calls"

    @property
    def cooldown_seconds(self) -> float:
        return 8.0  # Fast response for objection handling

    @property
    def required_data_sources(self) -> List[str]:
        return ["document_rag", "entity_extraction"]

    def should_activate(self, session: Any, segment: TranscriptSegment) -> bool:
        """Activate on prospect (non-user) segments and on user segments with questions.
        Prospects = objections. Users asking questions = coaching opportunity."""
        if segment.speaker == "user":
            # Only activate for user segments if they contain a question
            # (opportunity to suggest what the rep should ask next)
            return "?" in segment.text and len(segment.text.strip()) > 15
        # Always activate on prospect/other speaker segments
        return len(segment.text.strip()) > 15

    def build_context(self, session: Any) -> AgentContext:
        """Assemble context for sales coaching."""
        from agents.session import session_manager

        # Transcript window
        transcript_window = session_manager.format_transcript_window(session, last_n=10)

        # Company/role from session
        company = session.get("company", "")
        config = session.get("config", {})
        prospect_role = config.get("prospect_role", "decision maker")

        # BANT status from agent state
        agent_state = session_manager.get_agent_state(session, self.agent_type.value)
        bant = agent_state.get("bant", {
            "budget": "unknown",
            "authority": "unknown",
            "need": "unknown",
            "timeline": "unknown",
        })

        # Document RAG for battle cards
        document_rag_results = []
        buffer = session.get("transcript_buffer", [])
        last_text = buffer[-1].get("text", "") if buffer else ""
        if last_text:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    document_rag_results = loop.run_until_complete(
                        query_document_rag(last_text, top_k=3)
                    )
            except Exception:
                pass  # nosec B110

        return AgentContext(
            transcript_window=transcript_window,
            document_rag_results=document_rag_results,
            bant_status=bant,
            session_metadata={
                "company": company,
                "prospect_role": prospect_role,
            },
        )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the sales coaching prompt."""
        company = context.session_metadata.get("company", "Unknown company")
        prospect_role = context.session_metadata.get("prospect_role", "decision maker")
        bant = context.bant_status

        has_rag = bool(context.document_rag_results)

        if has_rag:
            from agents.context_builder import format_rag_results
            rag_str = format_rag_results(context.document_rag_results)
        else:
            rag_str = "No battle cards or product docs uploaded."

        if context.transcript_window and len(context.transcript_window) > 50:
            return SALES_COACH_PROMPT.format(
                company=company,
                prospect_role=prospect_role,
                transcript_window=context.transcript_window,
                document_rag_results=rag_str,
                bant_budget=bant.get("budget", "unknown"),
                bant_authority=bant.get("authority", "unknown"),
                bant_need=bant.get("need", "unknown"),
                bant_timeline=bant.get("timeline", "unknown"),
            )
        else:
            return SALES_COACH_PROMPT_MINIMAL.format(
                transcript_window=context.transcript_window or "(call just started)",
            )

    def parse_suggestions(self, raw_response: str, context: AgentContext) -> List[AgentSuggestion]:
        """Parse sales coaching output into structured suggestions."""
        suggestions = []

        lines = raw_response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # OBJECTION|type|prospect's words
            if line.upper().startswith("OBJECTION|"):
                parts = line.split("|", 2)
                if len(parts) >= 3 and parts[1].upper() != "NO_OBJECTION":
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="objection",
                        content=f"Objection ({parts[1]}): \"{parts[2]}\"",
                        confidence=0.88,
                        metadata={"objection_type": parts[1], "prospect_words": parts[2]},
                    ))

            # REBUTTAL|suggested response
            elif line.upper().startswith("REBUTTAL|"):
                content = line.split("|", 1)[1].strip() if "|" in line else line[9:].strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="rebuttal",
                        content=content,
                        confidence=0.82,
                        metadata={"type": "rebuttal"},
                    ))

            # BANT_UPDATE|dimension|new_status
            elif line.upper().startswith("BANT_UPDATE|"):
                parts = line.split("|", 2)
                if len(parts) >= 3:
                    dimension = parts[1].lower().strip()
                    new_status = parts[2].strip()
                    if dimension in ("budget", "authority", "need", "timeline"):
                        suggestions.append(AgentSuggestion(
                            id=self._new_suggestion_id(),
                            agent_type=self.agent_type.value,
                            category="talking_point",
                            content=f"BANT Update: {dimension.title()} → {new_status}",
                            confidence=0.85,
                            metadata={
                                "type": "bant_update",
                                "dimension": dimension,
                                "new_status": new_status,
                            },
                        ))

            # NEXT_QUESTION|question to ask
            elif line.upper().startswith("NEXT_QUESTION|"):
                content = line.split("|", 1)[1].strip() if "|" in line else line[14:].strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category="talking_point",
                        content=f"Ask: {content}",
                        confidence=0.78,
                        metadata={"type": "next_question"},
                    ))

        # Fallback: if no structured output parsed, create a general suggestion
        if not suggestions and raw_response.strip() and "NO_OBJECTION" not in raw_response.upper():
            suggestions.append(AgentSuggestion(
                id=self._new_suggestion_id(),
                agent_type=self.agent_type.value,
                category="talking_point",
                content=raw_response.strip()[:500],
                confidence=0.65,
                metadata={"type": "general", "parsed_fallback": True},
            ))

        return suggestions

    def update_bant_status(self, session: Any, suggestions: List[AgentSuggestion]) -> None:
        """Update BANT status in agent state based on parsed suggestions."""
        from agents.session import session_manager

        agent_state = session_manager.get_agent_state(session, self.agent_type.value)
        bant = agent_state.get("bant", {
            "budget": "unknown", "authority": "unknown",
            "need": "unknown", "timeline": "unknown",
        })

        for suggestion in suggestions:
            if suggestion.metadata.get("type") == "bant_update":
                dimension = suggestion.metadata.get("dimension", "")
                new_status = suggestion.metadata.get("new_status", "")
                if dimension in bant and new_status:
                    bant[dimension] = new_status

            if suggestion.category == "objection":
                agent_state["objections_detected"] = agent_state.get("objections_detected", 0) + 1

        session_manager.update_agent_state(
            session, self.agent_type.value,
            {"bant": bant}
        )