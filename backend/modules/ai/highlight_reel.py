"""AI-selected highlight reel generator — identifies key moments in conversations."""
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger("modules.ai.highlight_reel")

# Keyword patterns for key moment detection
DECISION_KEYWORDS = re.compile(
    r"\b(decided|decision|agreed|agreement|let'?s go with|we'll go with|approved|confirmed|finalized|committed|settled on)\b",
    re.IGNORECASE,
)
ACTION_ITEM_KEYWORDS = re.compile(
    r"\b(action item|todo|follow.?up|next step|deadline|assign|owner|responsible|will do|i'll|need to|must|should|by friday|by monday|by eod|by end of)\b",
    re.IGNORECASE,
)
IMPORTANCE_KEYWORDS = re.compile(
    r"\b(important|critical|urgent|priority|blocker|risk|escalat|key|crucial|essential|significant|milestone)\b",
    re.IGNORECASE,
)
QUESTION_PATTERN = re.compile(r"\?")

STYLE_WEIGHTS = {
    "balanced": {"decisions": 0.25, "action_items": 0.25, "importance": 0.25, "engagement": 0.25},
    "decisions": {"decisions": 0.50, "action_items": 0.15, "importance": 0.25, "engagement": 0.10},
    "action_items": {"decisions": 0.10, "action_items": 0.50, "importance": 0.25, "engagement": 0.15},
}


class HighlightReelGenerator:
    """Analyzes conversations to identify and select key moments for highlight reels."""

    def generate(
        self,
        conversation_messages: List[Dict],
        max_duration_seconds: int = 120,
        style: str = "balanced",
    ) -> List[Dict]:
        """Generate a highlight reel from conversation messages.

        Args:
            conversation_messages: List of message dicts with 'timestamp', 'speaker', 'text' keys.
            max_duration_seconds: Maximum total duration for the reel.
            style: One of 'balanced', 'decisions', 'action_items'.

        Returns:
            List of clip dicts with 'start', 'end', 'reason', 'confidence' keys.
        """
        if not conversation_messages:
            return []

        style = style if style in STYLE_WEIGHTS else "balanced"
        weights = STYLE_WEIGHTS[style]

        key_moments = self._identify_key_moments(conversation_messages)
        if not key_moments:
            return []

        # Score each key moment
        scored = []
        for moment in key_moments:
            scores = self._score_segment(conversation_messages, moment["start"], moment["end"])
            combined = (
                scores["decisions"] * weights["decisions"]
                + scores["action_items"] * weights["action_items"]
                + scores["importance"] * weights["importance"]
                + scores["engagement"] * weights["engagement"]
            )
            scored.append({
                **moment,
                "confidence": round(combined, 3),
                "reason": moment.get("reason", "key moment"),
            })

        # Sort by confidence descending
        scored.sort(key=lambda x: x["confidence"], reverse=True)

        # Select clips that fit within max_duration
        selected = []
        total_duration = 0
        used_timestamps = set()

        for clip in scored:
            clip_duration = clip["end"] - clip["start"]
            if total_duration + clip_duration > max_duration_seconds:
                continue
            # Avoid overlapping clips
            clip_range = range(int(clip["start"]), int(clip["end"]) + 1)
            if any(t in used_timestamps for t in clip_range):
                continue
            used_timestamps.update(clip_range)
            selected.append(clip)
            total_duration += clip_duration
            if total_duration >= max_duration_seconds:
                break

        # Sort by start time for playback order
        selected.sort(key=lambda x: x["start"])
        return selected

    def _score_segment(
        self, messages: List[Dict], start: float, end: float
    ) -> Dict[str, float]:
        """Score a segment on multiple dimensions (0-1 each)."""
        segment = [m for m in messages if start <= m.get("timestamp", 0) <= end]
        if not segment:
            return {"decisions": 0, "action_items": 0, "importance": 0, "engagement": 0}

        text = " ".join(m.get("text", "") for m in segment)

        # Decision score
        decision_matches = len(DECISION_KEYWORDS.findall(text))
        decisions = min(decision_matches / max(len(segment), 1) * 2, 1.0)

        # Action item score
        action_matches = len(ACTION_ITEM_KEYWORDS.findall(text))
        action_items = min(action_matches / max(len(segment), 1) * 2, 1.0)

        # Importance score
        importance_matches = len(IMPORTANCE_KEYWORDS.findall(text))
        importance = min(importance_matches / max(len(segment), 1) * 2, 1.0)

        # Engagement score (speaker changes + Q&A pairs)
        speakers = [m.get("speaker", "") for m in segment]
        speaker_changes = sum(
            1 for i in range(1, len(speakers)) if speakers[i] != speakers[i - 1]
        )
        questions = sum(1 for m in segment if QUESTION_PATTERN.search(m.get("text", "")))
        engagement = min((speaker_changes + questions) / max(len(segment), 1) * 1.5, 1.0)

        return {
            "decisions": round(decisions, 3),
            "action_items": round(action_items, 3),
            "importance": round(importance, 3),
            "engagement": round(engagement, 3),
        }

    def _identify_key_moments(self, messages: List[Dict]) -> List[Dict]:
        """Find timestamps of important moments in the conversation."""
        if not messages:
            return []

        moments = []
        timestamps = [m.get("timestamp", i * 30) for i, m in enumerate(messages)]

        for i, msg in enumerate(messages):
            text = msg.get("text", "")
            ts = timestamps[i]

            # Default segment: 15s before to 30s after the key message
            seg_start = max(ts - 15, 0)
            seg_end = ts + 30

            if DECISION_KEYWORDS.search(text):
                moments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "reason": "decision_made",
                })
            elif ACTION_ITEM_KEYWORDS.search(text):
                moments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "reason": "action_item",
                })
            elif IMPORTANCE_KEYWORDS.search(text):
                moments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "reason": "important_point",
                })

        # Also flag high-engagement segments (frequent speaker changes)
        window = 5
        for i in range(window, len(messages)):
            recent = messages[i - window : i]
            speakers = [m.get("speaker", "") for m in recent]
            unique_speakers = len(set(speakers))
            if unique_speakers >= 2:
                ts = timestamps[i - window]
                moments.append({
                    "start": ts,
                    "end": timestamps[i] + 5,
                    "reason": "high_engagement",
                })

        # Deduplicate overlapping moments
        if not moments:
            return []
        moments.sort(key=lambda x: x["start"])
        deduped = [moments[0]]
        for m in moments[1:]:
            if m["start"] - deduped[-1]["end"] < 5:
                deduped[-1]["end"] = max(deduped[-1]["end"], m["end"])
                if m["reason"] != deduped[-1]["reason"]:
                    deduped[-1]["reason"] = "mixed"
            else:
                deduped.append(m)

        return deduped


highlight_reel_generator = HighlightReelGenerator()