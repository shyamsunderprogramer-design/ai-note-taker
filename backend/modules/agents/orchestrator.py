"""
Agent Orchestrator — Routes transcript segments to active agents and merges their outputs.

Single entry point replacing both Shadow Agent and Realtime Suggestion Engine.
Fires all active agents in parallel, wraps SSE events with agent_type tags,
enforces per-agent cooldowns, and persists session state.
"""

import time
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator

from agents.base import (
    AgentType, AgentState, AgentSuggestion, AgentContext,
    BaseAgent, TranscriptSegment,
)
from agents.session import AgentSessionManager, session_manager
from agents.interview_coach import InterviewCoachAgent
from agents.meeting import MeetingAgent
from agents.sales_coach import SalesCoachAgent
from agents.context_builder import extract_entities
from agents.cache import get_cache, context_cache
from agents.learning import get_learner, suggestion_learner

logger = logging.getLogger("agents.orchestrator")


# SSE event helpers
def _make_event(event_type: str, data: Dict) -> str:
    """Create an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _make_agent_event(event_type: str, agent_type: str, **kwargs) -> str:
    """Create an SSE event string tagged with agent_type."""
    data = {"agent_type": agent_type, **kwargs}
    return _make_event(event_type, data)


def _make_no_suggestion() -> str:
    return _make_event("agent_noop", {"message": "No agents activated"})


def _make_error(message: str) -> str:
    return _make_event("agent_error", {"message": message})


class AgentOrchestrator:
    """Routes transcript segments to active agents and merges their outputs."""

    def __init__(self, sm: AgentSessionManager = None):
        self.session_manager = sm or session_manager
        self.agents: Dict[AgentType, BaseAgent] = {}
        self._register_agents()

    def _register_agents(self):
        """Register all available agent types."""
        self.agents[AgentType.INTERVIEW_COACH] = InterviewCoachAgent()
        self.agents[AgentType.MEETING] = MeetingAgent()
        self.agents[AgentType.SALES_COACH] = SalesCoachAgent()
        logger.info(f"[Orchestrator] Registered {len(self.agents)} agents: "
                     f"{[a.display_name for a in self.agents.values()]}")

    # Speaker mapping: convert diarizer labels to agent-friendly roles
    SPEAKER_ROLE_MAP = {
        "user": "user",
        "interviewer": "interviewer",
        "other": "other",
        "speaker 1": "user",       # Default assumption: Speaker 1 is the user
        "speaker 2": "interviewer",  # Speaker 2 is typically the other party
    }

    def normalize_speaker(self, speaker: str, session: Dict = None) -> str:
        """Normalize speaker labels from the diarizer to agent-compatible roles.

        Accepts:
          - Semantic roles from StreamingDiarizer: "user", "interviewer", "other", "other_N"
          - Raw labels from VibeVoice: "Speaker 1", "Speaker 2", "SPEAKER_00"
          - Custom mappings stored in session config

        Returns one of: "user", "interviewer", "other"
        """
        if not speaker:
            return "other"

        # Check session config for custom speaker mapping
        if session:
            speaker_map = session.get("config", {}).get("speaker_map", {})
            if speaker_map and speaker in speaker_map:
                return speaker_map[speaker]

        lower = speaker.lower().strip()

        # Direct match on known semantic roles
        if lower in ("user", "interviewer", "other"):
            return lower

        # "other_N" patterns from StreamingDiarizer
        if lower.startswith("other_"):
            return "other"

        # Raw speaker labels
        if lower in self.SPEAKER_ROLE_MAP:
            return self.SPEAKER_ROLE_MAP[lower]

        # SPEAKER_XX format
        if lower.startswith("speaker_"):
            try:
                num = int(lower.split("_")[1])
                if num == 0:
                    return "user"
                elif num == 1:
                    return "interviewer"
                else:
                    return "other"
            except (ValueError, IndexError):
                pass

        # "Speaker N" format
        if lower.startswith("speaker "):
            try:
                num = int(lower.split()[1])
                if num == 1:
                    return "user"
                elif num == 2:
                    return "interviewer"
                else:
                    return "other"
            except (ValueError, IndexError):
                pass

        # Default: unknown speakers are "other"
        return "other"

    def get_available_agents(self) -> List[Dict]:
        """List all available agent types with descriptions."""
        return [
            {
                "type": agent.agent_type.value,
                "name": agent.display_name,
                "description": agent.description,
                "cooldown_seconds": agent.cooldown_seconds,
                "data_sources": agent.required_data_sources,
            }
            for agent in self.agents.values()
        ]

    async def process_segment(
        self, session_id: str, text: str, speaker: str
    ) -> Dict:
        """Process a transcript segment and return JSON response (polling mode).

        This is the synchronous-friendly entry point that returns a complete
        response dict. For streaming, use process_segment_stream().

        speaker can be:
          - "user", "interviewer", "other" (semantic roles)
          - "Speaker 1", "Speaker 2" (raw diarizer labels)
          - "SPEAKER_00" (VibeVoice format)
        All are normalized to semantic roles via normalize_speaker().
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            return {"error": "Session not found", "suggestions": []}

        # Normalize speaker label to semantic role
        normalized_speaker = self.normalize_speaker(speaker, session)

        # Add segment to buffer
        segment = self.session_manager.add_segment(session, text, normalized_speaker)

        # Run entity extraction (cached in session)
        await self._extract_entities(session, text)

        # Collect suggestions from all active agents
        all_suggestions = []
        for agent_type_str in session.get("active_agents", []):
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                continue

            agent = self.agents.get(agent_type)
            if not agent:
                continue

            # Check activation and cooldown
            if not agent.should_activate(session, segment):
                continue
            if agent.is_in_cooldown(session):
                continue

            # Generate suggestions via LLM
            try:
                self._set_agent_state(session, agent_type.value, "thinking")
                suggestions = await self._run_agent_sync(agent, session)

                if suggestions:
                    all_suggestions.extend(suggestions)
                    # Update agent state
                    self._set_agent_state(session, agent_type.value, "suggesting")
                    agent.set_cooldown(session)
                    agent_state = self.session_manager.get_agent_state(session, agent_type.value)
                    agent_state["suggestions_made"] = agent_state.get("suggestions_made", 0) + len(suggestions)
                    self.session_manager.update_agent_state(session, agent_type.value, agent_state)

                    # Special: Meeting agent accumulates notes
                    if isinstance(agent, MeetingAgent):
                        agent.update_accumulated_notes(session, suggestions)

                    # Special: Sales coach updates BANT
                    if isinstance(agent, SalesCoachAgent):
                        agent.update_bant_status(session, suggestions)

            except Exception as e:
                logger.error(f"[Orchestrator] Agent {agent_type.value} error: {e}")
                self._set_agent_state(session, agent_type.value, "error")

        # Save session
        await self.session_manager.save_session(session)

        return {
            "session_id": session_id,
            "segment_processed": True,
            "suggestions": [s.to_dict() for s in all_suggestions],
            "suggestion_count": len(all_suggestions),
            "active_agents": session.get("active_agents", []),
        }

    async def process_segment_stream(
        self, session_id: str, text: str, speaker: str
    ) -> AsyncGenerator[str, None]:
        """Process a transcript segment and yield SSE events (streaming mode).

        Yields agent_chunk, agent_suggestion, agent_done, and agent_error events.

        speaker can be a semantic role or raw diarizer label — normalized internally.
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            yield _make_error("Session not found")
            return

        # Normalize speaker label to semantic role
        normalized_speaker = self.normalize_speaker(speaker, session)

        # Add segment to buffer
        segment = self.session_manager.add_segment(session, text, normalized_speaker)

        # Run entity extraction
        await self._extract_entities(session, text)

        # Notify frontend that processing has started
        yield _make_event("agent_processing", {
            "session_id": session_id,
            "segment_speaker": normalized_speaker,
            "segment_preview": text[:100],
        })

        # Track if any agent activated
        any_activated = False

        for agent_type_str in session.get("active_agents", []):
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                continue

            agent = self.agents.get(agent_type)
            if not agent:
                continue

            if not agent.should_activate(session, segment):
                continue
            if agent.is_in_cooldown(session):
                continue

            any_activated = True

            # Stream this agent's output
            try:
                self._set_agent_state(session, agent_type.value, "thinking")
                async for event in self._run_agent_stream(agent, session):
                    yield event

            except Exception as e:
                logger.error(f"[Orchestrator] Agent {agent_type.value} stream error: {e}")
                yield _make_agent_event("agent_error", agent_type.value, message=str(e))
                self._set_agent_state(session, agent_type.value, "error")

        if not any_activated:
            yield _make_no_suggestion()

        # Save session
        await self.session_manager.save_session(session)

    async def _run_agent_sync(self, agent: BaseAgent, session: Dict) -> List[AgentSuggestion]:
        """Run an agent synchronously and return parsed suggestions."""
        # Check context cache first
        current_question = ""
        buffer = session.get("transcript_buffer", [])
        for seg in reversed(buffer):
            if seg.get("speaker") != "user" and seg.get("is_question"):
                current_question = seg.get("text", "")
                break

        cached_context = context_cache.get(current_question) if current_question else None
        if cached_context:
            # Inject cached results into context building
            logger.debug(f"[Orchestrator] Cache hit for: {current_question[:50]}")

        context = agent.build_context(session)
        prompt = agent.build_prompt(context)

        # Inject learned hints from suggestion learner
        learned_hints = suggestion_learner.format_hints_for_prompt(agent.agent_type.value)
        if learned_hints:
            prompt = prompt + learned_hints

        # Collect the full streaming response
        full_response = ""
        try:
            from ai_router import route_ai_stream
        except ImportError:
            try:
                from modules.ai.ai_router import route_ai_stream
            except ImportError:
                from backend.modules.ai.ai_router import route_ai_stream

        provider = session.get("config", {}).get("provider", "ollama")

        for event in route_ai_stream(prompt, mode="interview", style="concise", provider=provider):
            # Parse SSE events to extract content
            if "event: chunk" in event:
                try:
                    data_line = [l for l in event.split("\n") if l.startswith("data:")]
                    if data_line:
                        data = json.loads(data_line[0][5:])
                        full_response += data.get("content", "")
                except (json.JSONDecodeError, IndexError):
                    pass
            elif "event: error" in event:
                logger.warning(f"[Orchestrator] LLM error for {agent.agent_type.value}")
                break

        # Parse the complete response into structured suggestions
        suggestions = agent.parse_suggestions(full_response, context)

        # Apply learned confidence boosts
        for s in suggestions:
            boost = suggestion_learner.get_confidence_boost(s.agent_type, s.category)
            s.confidence = min(1.0, max(0.0, s.confidence + boost))

        # Cache context results for similar future questions
        if current_question:
            context_cache.put(
                query=current_question,
                graph_results=context.cognitive_graph_results,
                rag_results=context.document_rag_results,
                company_insights=context.company_insights,
                entities=context.entities,
            )

        # Store suggestions in session
        for s in suggestions:
            self.session_manager.add_suggestion(session, s.to_dict())

        return suggestions

    async def _run_agent_stream(
        self, agent: BaseAgent, session: Dict
    ) -> AsyncGenerator[str, None]:
        """Run an agent and yield tagged SSE events."""
        context = agent.build_context(session)
        prompt = agent.build_prompt(context)
        agent_type_str = agent.agent_type.value

        # Inject learned hints from suggestion learner
        learned_hints = suggestion_learner.format_hints_for_prompt(agent_type_str)
        if learned_hints:
            prompt = prompt + learned_hints

        full_response = ""
        start_time = time.time()

        try:
            from ai_router import route_ai_stream
        except ImportError:
            try:
                from modules.ai.ai_router import route_ai_stream
            except ImportError:
                from backend.modules.ai.ai_router import route_ai_stream

        provider = session.get("config", {}).get("provider", "ollama")

        # Yield meta event
        yield _make_agent_event("agent_meta", agent_type_str,
                                name=agent.display_name, provider=provider)

        # Stream LLM chunks
        for event in route_ai_stream(prompt, mode="interview", style="concise", provider=provider):
            if "event: chunk" in event:
                try:
                    data_line = [l for l in event.split("\n") if l.startswith("data:")]
                    if data_line:
                        data = json.loads(data_line[0][5:])
                        content = data.get("content", "")
                        full_response += content
                        yield _make_agent_event("agent_chunk", agent_type_str, content=content)
                except (json.JSONDecodeError, IndexError):
                    pass
            elif "event: error" in event:
                try:
                    data_line = [l for l in event.split("\n") if l.startswith("data:")]
                    if data_line:
                        data = json.loads(data_line[0][5:])
                        yield _make_agent_event("agent_error", agent_type_str, message=data.get("message", "LLM error"))
                except (json.JSONDecodeError, IndexError):
                    yield _make_agent_event("agent_error", agent_type_str, message="LLM error")
                return

        # Parse the complete response into structured suggestions
        suggestions = agent.parse_suggestions(full_response, context)

        # Apply learned confidence boosts
        for s in suggestions:
            boost = suggestion_learner.get_confidence_boost(s.agent_type, s.category)
            s.confidence = min(1.0, max(0.0, s.confidence + boost))

        # Cache context results for similar future questions
        current_question = ""
        buffer = session.get("transcript_buffer", [])
        for seg in reversed(buffer):
            if seg.get("speaker") != "user" and seg.get("is_question"):
                current_question = seg.get("text", "")
                break
        if current_question:
            context_cache.put(
                query=current_question,
                graph_results=context.cognitive_graph_results,
                rag_results=context.document_rag_results,
                company_insights=context.company_insights,
                entities=context.entities,
            )

        elapsed = int((time.time() - start_time) * 1000)

        # Store suggestions in session
        for s in suggestions:
            self.session_manager.add_suggestion(session, s.to_dict())

        # Update agent state
        agent.set_cooldown(session)
        agent_state = self.session_manager.get_agent_state(session, agent_type_str)
        agent_state["suggestions_made"] = agent_state.get("suggestions_made", 0) + len(suggestions)
        self.session_manager.update_agent_state(session, agent_type_str, agent_state)

        # Special: Meeting agent accumulates notes
        if isinstance(agent, MeetingAgent):
            agent.update_accumulated_notes(session, suggestions)

        # Special: Sales coach updates BANT
        if isinstance(agent, SalesCoachAgent):
            agent.update_bant_status(session, suggestions)

        # Yield complete suggestions
        for s in suggestions:
            yield _make_agent_event("agent_suggestion", agent_type_str,
                                    suggestion=s.to_dict())

        # Yield done event
        yield _make_agent_event("agent_done", agent_type_str,
                                suggestion_count=len(suggestions), ms=elapsed)

    async def _extract_entities(self, session: Dict, text: str) -> None:
        """Run entity extraction and cache in session."""
        # Only extract if we don't have recent entities or text is new
        entities = session.get("entities", {})
        if not entities or len(text) > 50:
            new_entities = extract_entities(text)
            if new_entities:
                # Merge with existing
                for key in ("companies", "topics", "skills", "roles"):
                    existing = set(entities.get(key, []))
                    new_set = set(new_entities.get(key, []))
                    entities[key] = list(existing | new_set)
                entities["difficulty"] = new_entities.get("difficulty", entities.get("difficulty", "unknown"))
                session["entities"] = entities

    def _set_agent_state(self, session: Dict, agent_type: str, state: str) -> None:
        """Update agent state in session."""
        self.session_manager.update_agent_state(session, agent_type, {"state": state})


# Global singleton
orchestrator = AgentOrchestrator()