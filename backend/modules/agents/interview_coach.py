"""
Interview Coach Agent — LLM-powered real-time interview assistance.

Replaces the template-matching Shadow Agent with contextual LLM suggestions
that draw from the cognitive graph, document RAG, and entity extraction.
"""

import re
import logging
from typing import List, Dict, Any

from modules.agents.base import (
    BaseAgent, AgentType, AgentSuggestion, AgentContext,
    TranscriptSegment, is_question,
)
from modules.agents.context_builder import (
    query_cognitive_graph, query_document_rag, extract_entities,
    format_graph_results, format_rag_results, format_company_insights,
)
from modules.agents.prompts import INTERVIEW_COACH_PROMPT, INTERVIEW_COACH_PROMPT_MINIMAL

logger = logging.getLogger("agents.interview_coach")


class InterviewCoachAgent(BaseAgent):
    """LLM-powered interview coach that provides real-time suggestions
    using cognitive graph history, document RAG, and user profile context."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.INTERVIEW_COACH

    @property
    def display_name(self) -> str:
        return "Interview Coach"

    @property
    def description(self) -> str:
        return "Real-time interview assistance with AI-powered suggestions using your practice history and prep materials"

    @property
    def cooldown_seconds(self) -> float:
        return 10.0

    @property
    def required_data_sources(self) -> List[str]:
        return [
            "cognitive_graph", "document_rag", "entity_extraction",
            "user_profile", "company_insights",
        ]

    def should_activate(self, session: Any, segment: TranscriptSegment) -> bool:
        """Activate on interviewer questions only."""
        if segment.speaker == "user":
            return False
        if not segment.is_question:
            return False
        return True

    def build_context(self, session: Any) -> AgentContext:
        """Assemble rich context from all available data sources.

        Uses context cache to avoid redundant data source queries when
        similar questions have been asked recently.
        """
        from agents.session import session_manager

        # Transcript window (last 10 exchanges)
        transcript_window = session_manager.format_transcript_window(session, last_n=10)

        # Current question (most recent from transcript buffer)
        current_question = ""
        buffer = session.get("transcript_buffer", [])
        for seg in reversed(buffer):
            if seg.get("speaker") != "user" and seg.get("is_question"):
                current_question = seg.get("text", "")
                break

        # User profile from session config
        config = session.get("config", {})
        user_profile = config.get("user_profile", {})
        if not user_profile:
            role = session.get("role", "software engineer")
            company = session.get("company", "")
            user_profile = {
                "target_role": role,
                "target_company": company,
            }

        # Entities (cached in session)
        entities = session.get("entities", {})
        if not entities and current_question:
            entities = extract_entities(current_question)

        # Check context cache first — avoid redundant queries
        cache = get_cache()
        cached = cache.get(current_question) if current_question else None

        if cached:
            # Use cached results — significant latency savings
            cognitive_graph_results = cached.graph_results
            document_rag_results = cached.rag_results
            company_insights = cached.company_insights
            entities = entities or cached.entities
            logger.debug(f"[InterviewCoach] Cache hit for: {current_question[:50]}")
        else:
            # Cognitive graph results
            cognitive_graph_results = []
            if current_question:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        pass  # nosec B110
                    else:
                        cognitive_graph_results = loop.run_until_complete(
                            query_cognitive_graph(current_question, limit=5)
                        )
                except RuntimeError:
                    try:
                        from cognitive_graph import cognitive_graph
                        if hasattr(cognitive_graph, 'driver') and cognitive_graph.driver:
                            results = cognitive_graph.semantic_search(current_question, limit=5)
                            cognitive_graph_results = results or []
                    except Exception:
                        pass

            # Company insights
            company = session.get("company", "")
            company_insights = {}
            if company:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if not loop.is_running():
                        company_insights = loop.run_until_complete(
                            get_company_insights(company)
                        )
                except Exception:
                    pass  # nosec B110

            # Document RAG
            document_rag_results = []
            if current_question:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if not loop.is_running():
                        document_rag_results = loop.run_until_complete(
                            query_document_rag(current_question, top_k=3)
                        )
                except Exception:
                    pass  # nosec B110

            # Cache the results for future similar questions
            if current_question:
                cache.put(
                    query=current_question,
                    graph_results=cognitive_graph_results,
                    rag_results=document_rag_results,
                    company_insights=company_insights,
                    entities=entities,
                )

        return AgentContext(
            transcript_window=transcript_window,
            entities=entities,
            cognitive_graph_results=cognitive_graph_results,
            document_rag_results=document_rag_results,
            user_profile=user_profile,
            session_metadata={
                "questions_asked": len([s for s in buffer if s.get("speaker") != "user" and s.get("is_question")]),
                "company": session.get("company", ""),
                "role": session.get("role", ""),
                "stage": session.get("stage", ""),
            },
            company_insights=company_insights,
            current_question=current_question,
        )

    def build_prompt(self, context: AgentContext) -> str:
        """Build the full LLM prompt from assembled context."""
        company = context.session_metadata.get("company", "the company")
        role = context.session_metadata.get("role", "the role")

        # Check if we have enough context for the full prompt
        has_graph = bool(context.cognitive_graph_results)
        has_rag = bool(context.document_rag_results)
        has_insights = bool(context.company_insights)

        if has_graph or has_rag or has_insights:
            # Full prompt with all context
            user_profile_str = self._format_user_profile(context.user_profile)
            graph_str = format_graph_results(context.cognitive_graph_results) if has_graph else "No past practice data available for this question."
            rag_str = format_rag_results(context.document_rag_results) if has_rag else "No preparation materials uploaded."
            insights_str = format_company_insights(context.company_insights, company) if has_insights else f"No specific insights available for {company}."

            return INTERVIEW_COACH_PROMPT.format(
                role=role,
                company=company,
                user_profile=user_profile_str,
                transcript_window=context.transcript_window or "(no conversation yet)",
                cognitive_graph_results=graph_str,
                document_rag_results=rag_str,
                company_insights=insights_str,
                current_question=context.current_question,
            )
        else:
            # Minimal prompt — no external data, just the question
            return INTERVIEW_COACH_PROMPT_MINIMAL.format(
                role=role,
                current_question=context.current_question,
            )

    def parse_suggestions(self, raw_response: str, context: AgentContext) -> List[AgentSuggestion]:
        """Parse structured LLM output into AgentSuggestion objects.

        Expected format:
        [1] (confidence: 0.XX) category: suggestion text
        """
        suggestions = []
        # Regex pattern for structured output
        pattern = r'\[(\d+)\]\s*\(confidence:\s*(0?\.\d+)\)\s*(\w+):\s*(.+)'
        matches = re.findall(pattern, raw_response)

        if matches:
            for num, conf_str, category, text in matches:
                suggestions.append(AgentSuggestion(
                    id=self._new_suggestion_id(),
                    agent_type=self.agent_type.value,
                    category=category if category in (
                        "technical", "behavioral", "clarification", "strategic", "stalling"
                    ) else self._parse_category(category + " " + text),
                    content=text.strip(),
                    confidence=min(1.0, max(0.0, float(conf_str))),
                    metadata={
                        "hotkey": f"Ctrl+{num}",
                        "question": context.current_question,
                    },
                ))

        # Fallback: if regex didn't match, try line-by-line parsing
        if not suggestions:
            lines = [l.strip() for l in raw_response.strip().split("\n") if l.strip()]
            for i, line in enumerate(lines[:3], 1):
                # Try to extract confidence and category from the line
                confidence = self._parse_confidence(line)
                category = self._parse_category(line)
                # Remove confidence/category markers from content
                content = re.sub(r'\[\d+\]\s*', '', line)
                content = re.sub(r'\(confidence:\s*0?\.\d+\)\s*', '', content)
                content = re.sub(r'(technical|behavioral|clarification|strategic|stalling):\s*', '', content, count=1)
                content = content.strip()
                if content:
                    suggestions.append(AgentSuggestion(
                        id=self._new_suggestion_id(),
                        agent_type=self.agent_type.value,
                        category=category,
                        content=content,
                        confidence=confidence,
                        metadata={
                            "hotkey": f"Ctrl+{i}",
                            "question": context.current_question,
                        },
                    ))

        # Last resort: use the entire response as one suggestion
        if not suggestions and raw_response.strip():
            suggestions.append(AgentSuggestion(
                id=self._new_suggestion_id(),
                agent_type=self.agent_type.value,
                category=self._parse_category(raw_response),
                content=raw_response.strip()[:500],
                confidence=0.70,
                metadata={
                    "hotkey": "Ctrl+1",
                    "question": context.current_question,
                    "parsed_fallback": True,
                },
            ))

        return suggestions[:3]  # Max 3 suggestions

    def _format_user_profile(self, profile: Dict) -> str:
        """Format user profile for prompt injection."""
        if not profile:
            return "No specific profile information available."

        parts = []
        if profile.get("target_role"):
            parts.append(f"Target role: {profile['target_role']}")
        if profile.get("target_company"):
            parts.append(f"Target company: {profile['target_company']}")
        if profile.get("resume_summary"):
            parts.append(f"Background: {profile['resume_summary']}")
        if profile.get("key_skills"):
            parts.append(f"Key skills: {', '.join(profile['key_skills'])}")

        return "\n".join(parts) if parts else "No specific profile information available."