"""
Self-Learning — Tracks suggestion acceptance patterns to improve future prompts.

When a user accepts or dismisses a suggestion, the learning system records:
  - Which prompt patterns led to accepted suggestions
  - Which categories and confidence levels correlate with acceptance
  - Which agent types produce the most useful suggestions

This data is used to:
  - Boost confidence scores for patterns that have been accepted before
  - Adjust prompt templates to emphasize successful approaches
  - Deprioritize categories that are consistently dismissed
  - Generate "learned hints" that are injected into agent prompts
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("agents.learning")


@dataclass
class SuggestionFeedback:
    """Record of user feedback on a suggestion."""
    suggestion_id: str
    agent_type: str
    category: str
    content_preview: str
    confidence: float
    accepted: bool
    timestamp: float = 0.0
    question_hash: str = ""  # Hash of the triggering question
    prompt_version: str = ""  # Which prompt template was used

    def to_dict(self) -> Dict:
        return {
            "suggestion_id": self.suggestion_id,
            "agent_type": self.agent_type,
            "category": self.category,
            "accepted": self.accepted,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentPerformance:
    """Performance metrics for a specific agent type."""
    total_suggestions: int = 0
    accepted: int = 0
    dismissed: int = 0
    acceptance_rate: float = 0.0
    category_stats: Dict[str, Dict] = field(default_factory=dict)
    avg_confidence_accepted: float = 0.0
    avg_confidence_dismissed: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_suggestions": self.total_suggestions,
            "accepted": self.accepted,
            "dismissed": self.dismissed,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "category_stats": self.category_stats,
            "avg_confidence_accepted": round(self.avg_confidence_accepted, 3),
            "avg_confidence_dismissed": round(self.avg_confidence_dismissed, 3),
        }


class SuggestionLearner:
    """Tracks suggestion feedback and generates learning signals for prompts.

    Thread-safe. Persists learning data to session state so it survives
    across multiple segments within a session.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._feedback: List[SuggestionFeedback] = []
        self._lock = threading.Lock()
        self._agent_performance: Dict[str, AgentPerformance] = {}
        self._category_boost: Dict[str, float] = {}
        self._question_patterns: Dict[str, Dict] = {}

    def record_acceptance(
        self,
        suggestion_id: str,
        agent_type: str,
        category: str,
        content_preview: str,
        confidence: float,
        question_hash: str = "",
        prompt_version: str = "",
    ) -> None:
        """Record that a user accepted a suggestion."""
        feedback = SuggestionFeedback(
            suggestion_id=suggestion_id,
            agent_type=agent_type,
            category=category,
            content_preview=content_preview[:200],
            confidence=confidence,
            accepted=True,
            timestamp=time.time(),
            question_hash=question_hash,
            prompt_version=prompt_version,
        )
        self._record(feedback)

    def record_dismissal(
        self,
        suggestion_id: str,
        agent_type: str,
        category: str,
        content_preview: str,
        confidence: float,
        question_hash: str = "",
        prompt_version: str = "",
    ) -> None:
        """Record that a user dismissed a suggestion."""
        feedback = SuggestionFeedback(
            suggestion_id=suggestion_id,
            agent_type=agent_type,
            category=category,
            content_preview=content_preview[:200],
            confidence=confidence,
            accepted=False,
            timestamp=time.time(),
            question_hash=question_hash,
            prompt_version=prompt_version,
        )
        self._record(feedback)

    def _record(self, feedback: SuggestionFeedback) -> None:
        """Record feedback and update performance metrics."""
        with self._lock:
            self._feedback.append(feedback)
            # Evict oldest if over limit
            if len(self._feedback) > self.max_history:
                self._feedback = self._feedback[-self.max_history:]

            # Update agent performance
            agent_key = feedback.agent_type
            if agent_key not in self._agent_performance:
                self._agent_performance[agent_key] = AgentPerformance()

            perf = self._agent_performance[agent_key]
            perf.total_suggestions += 1

            if feedback.accepted:
                perf.accepted += 1
                # Running average of accepted confidence
                n = perf.accepted
                perf.avg_confidence_accepted = (
                    (perf.avg_confidence_accepted * (n - 1) + feedback.confidence) / n
                )
            else:
                perf.dismissed += 1
                n = perf.dismissed
                perf.avg_confidence_dismissed = (
                    (perf.avg_confidence_dismissed * (n - 1) + feedback.confidence) / n
                )

            perf.acceptance_rate = perf.accepted / max(1, perf.total_suggestions)

            # Update category stats
            cat = feedback.category
            if cat not in perf.category_stats:
                perf.category_stats[cat] = {"accepted": 0, "dismissed": 0, "total": 0}
            perf.category_stats[cat]["total"] += 1
            if feedback.accepted:
                perf.category_stats[cat]["accepted"] += 1
            else:
                perf.category_stats[cat]["dismissed"] += 1

            # Update category boost
            self._update_category_boosts()

            # Update question patterns
            if feedback.question_hash:
                self._update_question_patterns(feedback)

    def _update_category_boosts(self) -> None:
        """Recalculate category confidence boosts based on acceptance rates."""
        all_categories = defaultdict(lambda: {"accepted": 0, "total": 0})

        for feedback in self._feedback[-200:]:  # Use last 200 for recency
            cat = feedback.category
            all_categories[cat]["total"] += 1
            if feedback.accepted:
                all_categories[cat]["accepted"] += 1

        self._category_boost = {}
        for cat, stats in all_categories.items():
            if stats["total"] >= 3:  # Need at least 3 data points
                acceptance_rate = stats["accepted"] / stats["total"]
                # Boost ranges from -0.2 (always dismissed) to +0.2 (always accepted)
                self._category_boost[cat] = (acceptance_rate - 0.5) * 0.4

    def _update_question_patterns(self, feedback: SuggestionFeedback) -> None:
        """Track which question patterns lead to accepted/dismissed suggestions."""
        qhash = feedback.question_hash
        if qhash not in self._question_patterns:
            self._question_patterns[qhash] = {
                "accepted_categories": defaultdict(int),
                "dismissed_categories": defaultdict(int),
            }

        pattern = self._question_patterns[qhash]
        if feedback.accepted:
            pattern["accepted_categories"][feedback.category] += 1
        else:
            pattern["dismissed_categories"][feedback.category] += 1

    def get_confidence_boost(self, agent_type: str, category: str) -> float:
        """Get the confidence boost for a given agent type and category.

        Returns a value between -0.2 and +0.2 that should be added to
        the raw confidence score from the LLM.
        """
        with self._lock:
            boost = self._category_boost.get(category, 0.0)

            # Agent-specific boost
            perf = self._agent_performance.get(agent_type)
            if perf and perf.total_suggestions >= 5:
                # Scale agent acceptance rate to a small boost
                agent_boost = (perf.acceptance_rate - 0.5) * 0.1
                boost += agent_boost

            return max(-0.2, min(0.2, boost))

    def get_learned_hints(self, agent_type: str) -> List[str]:
        """Generate prompt hints based on learning data for a specific agent.

        These hints are injected into the prompt to guide the LLM toward
        producing more useful suggestions based on past user preferences.
        """
        hints = []

        with self._lock:
            perf = self._agent_performance.get(agent_type)
            if not perf or perf.total_suggestions < 5:
                return hints

            # Hint about overall acceptance rate
            if perf.acceptance_rate > 0.7:
                hints.append("User consistently values your suggestions — be specific and direct.")
            elif perf.acceptance_rate < 0.3:
                hints.append("User often dismisses suggestions — focus on actionable, concrete advice only.")

            # Hint about best-performing categories
            best_cats = sorted(
                [(cat, stats) for cat, stats in perf.category_stats.items() if stats["total"] >= 3],
                key=lambda x: x[1]["accepted"] / max(1, x[1]["total"]),
                reverse=True,
            )
            if best_cats:
                top_cats = [cat for cat, stats in best_cats[:3]
                            if stats["accepted"] / max(1, stats["total"]) > 0.5]
                if top_cats:
                    hints.append(f"User prefers {', '.join(top_cats)} suggestions — prioritize these categories.")

            # Hint about worst-performing categories
            worst_cats = [cat for cat, stats in best_cats[-2:]
                          if stats["accepted"] / max(1, stats["total"]) < 0.3]
            if worst_cats:
                hints.append(f"User rarely accepts {', '.join(worst_cats)} suggestions — avoid unless highly relevant.")

            # Hint about confidence calibration
            if perf.avg_confidence_accepted > perf.avg_confidence_dismissed + 0.1:
                hints.append("Higher-confidence suggestions tend to be more useful — be selective.")
            elif perf.avg_confidence_dismissed > perf.avg_confidence_accepted:
                hints.append("Confidence doesn't always mean relevance — focus on practicality over certainty.")

        return hints

    def format_hints_for_prompt(self, agent_type: str) -> str:
        """Format learned hints as a string suitable for prompt injection."""
        hints = self.get_learned_hints(agent_type)
        if not hints:
            return ""

        lines = ["\nLEARNED INSIGHTS (based on your past interactions with this user):"]
        for i, hint in enumerate(hints, 1):
            lines.append(f"{i}. {hint}")
        return "\n".join(lines)

    def get_performance_stats(self, agent_type: Optional[str] = None) -> Dict:
        """Get performance statistics for one or all agents."""
        with self._lock:
            if agent_type:
                perf = self._agent_performance.get(agent_type)
                return perf.to_dict() if perf else {}

            return {
                "feedback_count": len(self._feedback),
                "agents": {
                    atype: perf.to_dict()
                    for atype, perf in self._agent_performance.items()
                },
                "category_boosts": dict(self._category_boost),
            }

    def load_from_session(self, session: Dict) -> None:
        """Load learning state from a session dict (for persistence)."""
        learning_data = session.get("learning_state", {})
        if not learning_data:
            return

        with self._lock:
            # Restore agent performance
            for agent_type, perf_dict in learning_data.get("agent_performance", {}).items():
                perf = AgentPerformance(
                    total_suggestions=perf_dict.get("total_suggestions", 0),
                    accepted=perf_dict.get("accepted", 0),
                    dismissed=perf_dict.get("dismissed", 0),
                    acceptance_rate=perf_dict.get("acceptance_rate", 0.0),
                    category_stats=perf_dict.get("category_stats", {}),
                    avg_confidence_accepted=perf_dict.get("avg_confidence_accepted", 0.0),
                    avg_confidence_dismissed=perf_dict.get("avg_confidence_dismissed", 0.0),
                )
                self._agent_performance[agent_type] = perf

            # Restore category boosts
            self._category_boost = learning_data.get("category_boosts", {})

    def save_to_session(self, session: Dict) -> None:
        """Save learning state to a session dict (for persistence)."""
        with self._lock:
            session["learning_state"] = {
                "agent_performance": {
                    atype: perf.to_dict()
                    for atype, perf in self._agent_performance.items()
                },
                "category_boosts": dict(self._category_boost),
                "feedback_count": len(self._feedback),
            }


# Global learner singleton
suggestion_learner = SuggestionLearner()


def get_learner() -> SuggestionLearner:
    """Get the global suggestion learner instance."""
    return suggestion_learner