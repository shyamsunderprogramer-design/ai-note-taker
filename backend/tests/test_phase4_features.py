"""Tests for Phase 4-6 features: integrations, video, career, compliance.

Integration tests (Calendar, Slack, Teams, etc.) require a running server.
Unit tests (HighlightReel) run standalone.
"""
import os
import sys
import pytest

# Set test env before any imports
os.environ["USE_SQLITE"] = "true"
os.environ["AUTH_REQUIRED"] = "false"
os.environ["TESTING"] = "true"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS (no server required)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHighlightReel:
    @pytest.fixture(autouse=True)
    def setup(self):
        from modules.ai.highlight_reel import HighlightReelGenerator
        self.gen = HighlightReelGenerator()

    def test_empty_messages(self):
        result = self.gen.generate([], 120, "balanced")
        assert result == []

    def test_decision_detection(self):
        msgs = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to go with option B."},
            {"timestamp": 60, "speaker": "B", "text": "Okay let's proceed."},
        ]
        result = self.gen.generate(msgs, 120, "decisions")
        assert len(result) >= 1

    def test_action_item_detection(self):
        msgs = [
            {"timestamp": 0, "speaker": "A", "text": "I'll follow up on that action item."},
            {"timestamp": 60, "speaker": "B", "text": "Make sure to do it by Friday."},
        ]
        result = self.gen.generate(msgs, 120, "action_items")
        assert len(result) >= 1

    def test_max_duration_respected(self):
        msgs = [
            {"timestamp": i * 30, "speaker": f"S{i%3}", "text": "We decided this is critical."}
            for i in range(20)
        ]
        result = self.gen.generate(msgs, 60, "balanced")
        total = sum(c["end"] - c["start"] for c in result)
        assert total <= 60

    def test_invalid_style_defaults_balanced(self):
        msgs = [{"timestamp": 0, "speaker": "A", "text": "Important decision made."}]
        result = self.gen.generate(msgs, 120, "invalid_style")
        assert isinstance(result, list)

    def test_score_segment(self):
        msgs = [
            {"timestamp": 0, "speaker": "A", "text": "We decided to launch."},
            {"timestamp": 30, "speaker": "B", "text": "I will follow up."},
        ]
        scores = self.gen._score_segment(msgs, 0, 60)
        assert "decisions" in scores
        assert "action_items" in scores
        assert all(0 <= v <= 1 for v in scores.values())


class TestCognitiveGraphMemory:
    def test_add_and_find_node(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        nid = g.add_node("Company", {"name": "Google"})
        found = g.find_node("Company", "name", "Google")
        assert found is not None
        assert found.id == nid

    def test_add_edge_and_neighbors(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        a = g.add_node("User", {"name": "alice"})
        b = g.add_node("Skill", {"name": "Python"})
        g.add_edge(a, b, "HAS_SKILL")
        neighbors = g.get_neighbors(a, "HAS_SKILL")
        assert len(neighbors) == 1

    def test_interview_recording(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        iid = g.add_interview("alice", "Google", "SWE",
            [{"text": "Reverse a list", "topic": "coding", "category": "coding"}],
            [{"text": "Two pointers", "quality": "good", "confidence": 0.9}])
        assert iid is not None
        stats = g.get_stats()
        assert stats["total_nodes"] >= 5

    def test_user_skills(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        g.add_skill("bob", "Go", "expert")
        g.add_skill("bob", "Rust", "intermediate")
        skills = g.get_user_skills("bob")
        assert len(skills) == 2
        assert any(s["skill"] == "Go" for s in skills)

    def test_knowledge_graph_export(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        g.add_skill("carol", "Python", "expert")
        kg = g.get_knowledge_graph(user_id="carol")
        assert "nodes" in kg
        assert "edges" in kg
        assert len(kg["nodes"]) >= 2

    def test_dedup_by_name(self):
        from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph
        g = InMemoryCognitiveGraph()
        a = g.add_node("Company", {"name": "Meta"})
        b = g.add_node("Company", {"name": "Meta"})
        assert a == b  # Same node returned for same name

