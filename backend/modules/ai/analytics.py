"""
analytics.py - Conversation Analytics for AI Note Taker

Tracks and analyzes conversation patterns over time:
- Conversation frequency and duration
- AI model usage breakdown
- Speaker participation ratios
- Response time patterns
- Mode usage statistics
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger("analytics")

# Storage path
DATA_DIR = Path(os.path.dirname(__file__)) / "data"
ANALYTICS_FILE = DATA_DIR / "analytics.json"

# Ensure directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ConversationMetrics:
    """Metrics for a single conversation."""
    conversation_id: str
    start_time: float
    end_time: float
    duration_minutes: float
    message_count: int
    user_message_count: int
    ai_message_count: int
    modes_used: List[str]
    models_used: List[str]
    avg_response_time_seconds: Optional[float] = None
    total_tokens: int = 0


@dataclass
class DailyMetrics:
    """Aggregated metrics for a single day."""
    date: str
    conversation_count: int = 0
    total_duration_minutes: float = 0.0
    total_messages: int = 0
    messages_by_role: Dict[str, int] = None
    messages_by_mode: Dict[str, int] = None
    messages_by_model: Dict[str, int] = None

    def __post_init__(self):
        if self.messages_by_role is None:
            self.messages_by_role = {"user": 0, "assistant": 0}
        if self.messages_by_mode is None:
            self.messages_by_mode = {}
        if self.messages_by_model is None:
            self.messages_by_model = {}


class AnalyticsStore:
    """Manages conversation analytics data."""

    def __init__(self):
        self.conversations: List[ConversationMetrics] = []
        self.daily: Dict[str, DailyMetrics] = {}
        self._load()

    def _load(self):
        """Load analytics data from disk."""
        if ANALYTICS_FILE.exists():
            try:
                with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.conversations = [
                        ConversationMetrics(**c) for c in data.get("conversations", [])
                    ]
                    self.daily = {
                        k: DailyMetrics(**v) for k, v in data.get("daily", {}).items()
                    }
                logger.info(f"Loaded analytics: {len(self.conversations)} conversations")
            except Exception as e:
                logger.warning("Failed to load analytics: %s", str(e))

    def _save(self):
        """Save analytics data to disk."""
        try:
            with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "conversations": [asdict(c) for c in self.conversations],
                    "daily": {k: asdict(v) for k, v in self.daily.items()}
                }, f, indent=2)
        except Exception as e:
            logger.error("Failed to save analytics: %s", str(e))

    def record_conversation(self, conversation_id: str, messages: List[Dict],
                           start_time: float, end_time: float,
                           models_used: List[str] = None) -> ConversationMetrics:
        """Record metrics for a completed conversation."""
        duration = (end_time - start_time) / 60  # Convert to minutes

        user_msgs = [m for m in messages if m.get("role") == "user"]
        ai_msgs = [m for m in messages if m.get("role") == "assistant"]

        modes = list(set(m.get("mode", "adaptive") for m in messages if m.get("mode")))
        models = models_used or []

        # Calculate average response time (simplified)
        avg_response_time = None
        if len(messages) > 1:
            response_times = []
            for i in range(1, len(messages)):
                prev_msg = messages[i-1]
                curr_msg = messages[i]
                if prev_msg.get("role") == "user" and curr_msg.get("role") == "assistant":
                    prev_time = prev_msg.get("timestamp", 0)
                    curr_time = curr_msg.get("timestamp", 0)
                    if curr_time > prev_time:
                        response_times.append((curr_time - prev_time) / 1000)  # ms to seconds
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        metrics = ConversationMetrics(
            conversation_id=conversation_id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            message_count=len(messages),
            user_message_count=len(user_msgs),
            ai_message_count=len(ai_msgs),
            modes_used=modes,
            models_used=models,
            avg_response_time_seconds=avg_response_time,
            total_tokens=sum(len(m.get("text", "")) for m in messages) // 4  # Rough token estimate
        )

        self.conversations.append(metrics)

        # Update daily metrics
        date_key = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")
        if date_key not in self.daily:
            self.daily[date_key] = DailyMetrics(date=date_key)

        daily = self.daily[date_key]
        daily.conversation_count += 1
        daily.total_duration_minutes += duration
        daily.total_messages += len(messages)
        daily.messages_by_role["user"] += len(user_msgs)
        daily.messages_by_role["assistant"] += len(ai_msgs)

        for mode in modes:
            daily.messages_by_mode[mode] = daily.messages_by_mode.get(mode, 0) + 1

        for model in models:
            daily.messages_by_model[model] = daily.messages_by_model.get(model, 0) + 1

        self._save()
        logger.info(f"Recorded analytics for conversation {conversation_id}")
        return metrics

    def get_summary(self, days: int = 30) -> Dict:
        """Get analytics summary for the past N days."""
        cutoff = time.time() - (days * 24 * 60 * 60)
        recent = [c for c in self.conversations if c.start_time >= cutoff]

        if not recent:
            return {
                "period_days": days,
                "total_conversations": 0,
                "message": "No conversations in this period"
            }

        total_duration = sum(c.duration_minutes for c in recent)
        total_messages = sum(c.message_count for c in recent)
        total_user = sum(c.user_message_count for c in recent)
        total_ai = sum(c.ai_message_count for c in recent)

        # Calculate averages
        avg_duration = total_duration / len(recent)
        avg_messages = total_messages / len(recent)

        # Mode breakdown
        mode_counts = defaultdict(int)
        for c in recent:
            for mode in c.modes_used:
                mode_counts[mode] += 1

        # Model breakdown
        model_counts = defaultdict(int)
        for c in recent:
            for model in c.models_used:
                model_counts[model] += 1

        # Response time stats
        response_times = [c.avg_response_time_seconds for c in recent
                         if c.avg_response_time_seconds is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        # Daily trend (last 7 days)
        daily_trend = []
        for i in range(6, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            if date_key in self.daily:
                daily_trend.append({
                    "date": date_key,
                    "conversations": self.daily[date_key].conversation_count,
                    "messages": self.daily[date_key].total_messages
                })
            else:
                daily_trend.append({
                    "date": date_key,
                    "conversations": 0,
                    "messages": 0
                })

        return {
            "period_days": days,
            "total_conversations": len(recent),
            "total_duration_minutes": round(total_duration, 2),
            "total_messages": total_messages,
            "user_messages": total_user,
            "ai_messages": total_ai,
            "speaker_ratio": round(total_user / total_ai, 2) if total_ai > 0 else 0,
            "avg_conversation_duration_minutes": round(avg_duration, 2),
            "avg_messages_per_conversation": round(avg_messages, 2),
            "avg_response_time_seconds": round(avg_response_time, 2) if avg_response_time else None,
            "mode_breakdown": dict(mode_counts),
            "model_breakdown": dict(model_counts),
            "daily_trend": daily_trend
        }

    def get_export_data(self, format: str = "json") -> Dict:
        """Export analytics data."""
        if format == "csv":
            # Generate CSV
            lines = ["date,conversation_count,total_messages,user_messages,ai_messages"]
            for date_key in sorted(self.daily.keys()):
                d = self.daily[date_key]
                lines.append(f"{date_key},{d.conversation_count},{d.total_messages},"
                           f"{d.messages_by_role.get('user', 0)},{d.messages_by_role.get('assistant', 0)}")
            return {
                "content": "\n".join(lines),
                "filename": f"analytics-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
            }
        else:
            return {
                "content": json.dumps({
                    "export_date": datetime.now().isoformat(),
                    "conversations": [asdict(c) for c in self.conversations],
                    "daily_summary": {k: asdict(v) for k, v in self.daily.items()}
                }, indent=2),
                "filename": f"analytics-export-{datetime.now().strftime('%Y-%m-%d')}.json"
            }


# Global analytics store instance
_analytics_store = None


def get_analytics_store() -> AnalyticsStore:
    """Get the global analytics store instance."""
    global _analytics_store
    if _analytics_store is None:
        _analytics_store = AnalyticsStore()
    return _analytics_store
