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

        try:
            # Query cognitive graph for similar questions
            similar = cognitive_graph.semantic_search(segment.text, limit=3)

            if not similar:
                # Try with extracted keywords
                keywords = self._extract_keywords(segment.text)
                if keywords:
                    similar = cognitive_graph.semantic_search(" ".join(keywords), limit=3)

            if not similar:
                return None
        except Exception as e:
            logger.error("[RealtimeSuggestions] Error querying graph: %s", str(e))
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
        if not COGNITIVE_GRAPH_AVAILABLE:
            return None

        text_lower = text.lower().strip()

        # Check for search commands
        for pattern in self.COMMAND_PATTERNS["search"]:
            match = re.search(pattern, text_lower)
            if match:
                query = match.group(1).strip()
                try:
                    results = cognitive_graph.semantic_search(query, limit=5)
                    return {
                        "action": "search_results",
                        "query": query,
                        "results": results
                    }
                except Exception as e:
                    logger.error("[VoiceCommand] Search error: %s", str(e))
                    return {"action": "error", "message": "Search failed"}

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


# ---------------------------------------------------------------------------
# Live LLM generation (wired into /ws/transcribe)
#
# The template engine above answers every question with the same canned
# "stalling" line. This path generates a real, context-aware answer from a
# locally installed Ollama model — question + candidate context in, first-person
# answer out — so the overlay shows something the candidate can actually say.
# Blocking HTTP; callers must run it in a worker thread.
# ---------------------------------------------------------------------------

import os as _os
import time as _time

_LIVE_MODEL = _os.getenv("ANT_LIVE_MODEL", "qwen3.5:9b")
_LIVE_TIMEOUT = float(_os.getenv("ANT_LIVE_TIMEOUT", "12"))
# How long Ollama holds the live model in memory after a request.
# Interviews have long gaps between questions; the default 5m would
# evict mid-interview and make the next question pay the cold penalty.
_LIVE_KEEP_ALIVE = _os.getenv("ANT_LIVE_KEEP_ALIVE", "30m")


def generate_live_suggestion(
    question: str,
    role: str = "",
    company: str = "",
    skills: str = "",
    resume: str = "",
    model: str = None,
    history: list = None,
    on_first_sentence=None,
) -> dict:
    """Generate a concise first-person interview answer for one question.

    Returns {"text": str|None, "gen_ms": int, "model": str, "error": str|None}.
    Falls back to the template engine's output when Ollama is unreachable.
    """
    from config import OLLAMA_URL  # matches sibling modules/ai/ai_router.py convention

    used_model = model or _LIVE_MODEL
    t0 = _time.perf_counter()
    # Prior turns make the answer part of a conversation instead of a series of
    # unrelated statements: it stops the model re-introducing the candidate for
    # every question and lets it build on what was already claimed.
    recap = ""
    if history:
        lines = []
        for turn in history[-3:]:
            q = (turn.get("question") or "").strip()
            a = (turn.get("answer") or "").strip()
            if q and a:
                lines.append(f"- They asked: \"{q}\" and you answered: \"{a}\"")
        if lines:
            recap = (
                "Earlier AI drafts (not verified candidate facts):\n" + "\n".join(lines) +
                "\n\nUse these only to avoid repetition. They are not evidence of "
                "experience; discard any detail unsupported by the candidate context.\n\n"
            )

    prompt = (
        "You are a live interview assistant whispering answers to a candidate. "
        + recap +
        f"The interviewer just asked: \"{question.strip()}\"\n\n"
        f"Candidate context — role: {role or 'not provided'}; "
        f"company being interviewed at: {company or 'unknown'}; "
        f"skills: {skills or 'not provided'}; "
        f"resume highlights: {resume or 'not provided'}.\n\n"
        "Use only supplied candidate facts for personal experience. Never invent "
        "employers, dates, achievements, metrics, or project details. If experience "
        "is missing, give a short answer structure with bracketed placeholders instead. "
        "A result does not establish how it was measured. Use [measurement method] "
        "if the method is absent, and [project details] for absent implementation details. "
        "Reply in 2-3 sentences, under 50 words. For personal questions, use first "
        "person only for supplied facts and placeholders for missing facts. For "
        "technical questions, explain the concept directly without claiming personal experience. "
        "Answer exactly what was asked and nothing else — do not drift onto a "
        "different topic, and do not re-introduce the candidate when the "
        "conversation is already under way. "
        "No preamble, no markdown, no disclaimers — just the spoken answer."
    )
    payload_stream = on_first_sentence is not None
    if model and (model.endswith(":cloud") or ":" not in model):
        # Explicit cloud choices use the same provider mapping as typed requests.
        import asyncio
        from lib.live_model_stream import collect_selected_model
        try:
            text = asyncio.run(collect_selected_model(prompt, model, _LIVE_TIMEOUT))
            return {"text": text or None, "gen_ms": int((_time.perf_counter()-t0)*1000),
                    "model": model, "error": None if text else "empty response"}
        except Exception as exc:
            return {"text": None, "gen_ms": int((_time.perf_counter()-t0)*1000),
                    "model": model, "error": str(exc) or "Selected model timed out"}
    try:
        import json as _json

        import httpx

        if payload_stream:
            # Stream so the candidate can START TALKING at the first sentence
            # instead of waiting for the whole answer. The gate that matters is
            # time-to-first-speakable-sentence, and a complete 80-token answer
            # arrives seconds after the first sentence is already usable.
            return _stream_generate(
                OLLAMA_URL, used_model, prompt, t0, on_first_sentence
            )

        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": used_model,
                "prompt": prompt,
                "stream": False,
                "think": False,  # qwen3.5:9b puts content in `thinking` otherwise
                # Hold the model in VRAM between questions. Measured
                # 2026-09-11: cold generation ran 5.4-5.7s against a 4.0s
                # gate while warm ran 1.8-2.2s — the entire failure was model
                # load, repaid on every question after a quiet stretch.
                "keep_alive": _LIVE_KEEP_ALIVE,
                "options": {
                    "temperature": 0.4,
                    "num_predict": 80,
                    "num_ctx": 2048,
                },
            },
            timeout=_LIVE_TIMEOUT,
        )
        gen_ms = int((_time.perf_counter() - t0) * 1000)
        if resp.status_code != 200:
            return {
                "text": None,
                "gen_ms": gen_ms,
                "model": used_model,
                "error": f"ollama {resp.status_code}",
            }
        text = (resp.json().get("response") or "").strip()
        if not text:
            return {
                "text": None,
                "gen_ms": gen_ms,
                "model": used_model,
                "error": "empty response",
            }
        return {"text": text, "gen_ms": gen_ms, "model": used_model, "error": None}
    except Exception as exc:  # network down / timeout — degrade to template
        gen_ms = int((_time.perf_counter() - t0) * 1000)
        fallback = realtime_engine.process_segment(question, "interviewer")
        fb_text = fallback.content if fallback else None
        return {
            "text": fb_text,
            "gen_ms": gen_ms,
            "model": "template-fallback",
            "error": str(exc)[:120],
        }


def warmup_live_model(timeout: float = 60.0) -> dict:
    """Load the live-assist model before the first question arrives.

    keep_alive holds the model once it is resident, but nothing pays for the
    FIRST load — and in an interview the first question is the one that must
    not be slow. Called at startup, this moves that cost to boot time.
    """
    from config import OLLAMA_URL

    t0 = _time.perf_counter()
    try:
        import httpx

        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": _LIVE_MODEL,
                "prompt": "",          # empty prompt = load only, no generation
                "stream": False,
                "keep_alive": _LIVE_KEEP_ALIVE,
                "options": {"num_ctx": 2048},
            },
            timeout=timeout,
        )
        ms = int((_time.perf_counter() - t0) * 1000)
        ok = resp.status_code == 200
        return {"ok": ok, "model": _LIVE_MODEL, "ms": ms,
                "error": None if ok else f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"ok": False, "model": _LIVE_MODEL,
                "ms": int((_time.perf_counter() - t0) * 1000), "error": str(exc)}


# Rolling previews run repeatedly while the interviewer is still speaking, so
# they use a smaller model and a tighter budget than the committed answer. The
# 9B model is worth 2s once per question; it is not worth 2s every few seconds.
# Same model as the committed answer, deliberately. A second model has to be
# resident to be fast, and two of these do not fit together (gemma4:e4b 9.6GB +
# qwen3.5:9b 6.6GB on a 24GB machine), so Ollama evicted and reloaded between
# every preview and answer. Measured cost: first-sentence latency swinging
# between 1.5s and 6.9s with no relation to question length. Reusing the hot
# model makes a 40-token preview nearly free.
_PREVIEW_MODEL = _os.getenv("ANT_PREVIEW_MODEL", "") or _LIVE_MODEL
_PREVIEW_TIMEOUT = float(_os.getenv("ANT_PREVIEW_TIMEOUT", "6"))


def generate_live_preview(
    partial_question: str,
    role: str = "",
    company: str = "",
    skills: str = "",
    resume: str = "",
    history: list = None,
) -> dict:
    """One short line of direction while the question is still being asked.

    This is deliberately NOT a full answer. The question is incomplete, so
    committing to an answer invites drift onto the wrong point — the thing the
    candidate then has to talk their way back from. A single line of direction
    is useful early and costs little to be wrong about.
    """
    from config import OLLAMA_URL

    t0 = _time.perf_counter()
    recap = ""
    if history:
        last = history[-1]
        q = (last.get("question") or "").strip()
        if q:
            recap = f"The previous question was \"{q}\", already answered.\n"

    prompt = (
        "You are helping a candidate in a live interview. The interviewer is "
        "STILL SPEAKING and has said this much so far:\n\n"
        f"\"{partial_question.strip()}\"\n\n"
        f"{recap}"
        f"Candidate: {role or 'software engineer'} interviewing at "
        f"{company or 'the company'}; background: "
        f"{resume or 'experienced engineer'}.\n\n"
        "In ONE short sentence (under 20 words), say what to talk about when "
        "they finish. Stay strictly on what was actually asked — do not invent "
        "a different question. No preamble, no markdown."
    )
    try:
        import httpx

        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": _PREVIEW_MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "keep_alive": _LIVE_KEEP_ALIVE,
                "options": {"temperature": 0.3, "num_predict": 40, "num_ctx": 1024},
            },
            timeout=_PREVIEW_TIMEOUT,
        )
        gen_ms = int((_time.perf_counter() - t0) * 1000)
        if resp.status_code != 200:
            return {"text": None, "gen_ms": gen_ms, "model": _PREVIEW_MODEL,
                    "error": f"HTTP {resp.status_code}"}
        text = (resp.json().get("response") or "").strip()
        # Small models like to narrate; keep the first sentence only.
        for sep in ("\n", ". "):
            if sep in text:
                text = text.split(sep)[0].strip().rstrip(".") + ""
                break
        return {"text": text or None, "gen_ms": gen_ms,
                "model": _PREVIEW_MODEL, "error": None}
    except Exception as exc:
        return {"text": None, "gen_ms": int((_time.perf_counter() - t0) * 1000),
                "model": _PREVIEW_MODEL, "error": str(exc)}


_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def _stream_generate(ollama_url, model, prompt, t0, on_first_sentence):
    """Generate with streaming, surfacing the first sentence as soon as it lands."""
    import json as _json

    import httpx

    buf = ""
    fired = False
    try:
        with httpx.stream(
            "POST",
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "think": False,
                "keep_alive": _LIVE_KEEP_ALIVE,
                "options": {"temperature": 0.4, "num_predict": 80, "num_ctx": 2048},
            },
            timeout=_LIVE_TIMEOUT,
        ) as resp:
            if resp.status_code != 200:
                return {"text": None, "gen_ms": int((_time.perf_counter() - t0) * 1000),
                        "model": model, "error": f"ollama {resp.status_code}"}
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    obj = _json.loads(line)
                except ValueError:
                    continue
                buf += obj.get("response") or ""
                if not fired:
                    match = _SENTENCE_END.search(buf)
                    # A fragment is not speakable; wait for a real sentence.
                    if match and len(buf[: match.end()].split()) >= 6:
                        fired = True
                        try:
                            on_first_sentence(
                                buf[: match.end()].strip(),
                                int((_time.perf_counter() - t0) * 1000),
                            )
                        except Exception:
                            pass  # nosec B110 — delivery failure must not kill generation
                if obj.get("done"):
                    break
    except Exception as exc:
        return {"text": buf.strip() or None,
                "gen_ms": int((_time.perf_counter() - t0) * 1000),
                "model": model, "error": str(exc)[:120]}

    text = buf.strip()
    return {"text": text or None, "gen_ms": int((_time.perf_counter() - t0) * 1000),
            "model": model, "error": None if text else "empty response"}
