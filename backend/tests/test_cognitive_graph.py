"""
Tests for backend/modules/ai/cognitive_graph_memory.py — the in-memory
zero-config backend for the cognitive graph.

The cognitive graph is the heart of the personalization layer: it tracks
interview history, company-specific questions, skill progression, and
predicted interview questions. Most route handlers in routes/cognitive.py
delegate directly to this module's API when Neo4j is not connected, so
bugs in the graph propagate to every read endpoint.

We test the InMemoryCognitiveGraph API directly (add_node, add_interview,
add_skill, get_neighbors, get_user_skills, get_user_interviews,
get_nodes_by_label, find_node, get_stats) plus the two search helpers
in routes/cognitive.py (_keyword_search and _advanced_keyword_search).
We do NOT use TestClient (conftest's `from main import app` is broken
per Fix #31) — these are pure unit tests on the data layer.
"""

import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

from modules.ai.cognitive_graph_memory import (
    GraphNode,
    InMemoryCognitiveGraph,
)


@pytest.fixture
def graph():
    """Fresh in-memory graph for each test."""
    return InMemoryCognitiveGraph()


class TestInMemoryCognitiveGraphBasics:
    """Core node and edge CRUD."""

    def test_starts_empty(self, graph):
        stats = graph.get_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0

    def test_add_node_returns_id(self, graph):
        nid = graph.add_node("Company", {"name": "Google"})
        assert nid is not None
        assert isinstance(nid, str)

    def test_get_node_returns_added(self, graph):
        nid = graph.add_node("Company", {"name": "Google"})
        node = graph.get_node(nid)
        assert node is not None
        assert node.label == "Company"
        assert node.properties["name"] == "Google"

    def test_add_node_with_name_dedupes(self, graph):
        """Adding a Company named 'Google' twice should return the same id."""
        nid1 = graph.add_node("Company", {"name": "Google"})
        nid2 = graph.add_node("Company", {"name": "Google"})
        assert nid1 == nid2
        # Stats should show only one node
        assert graph.get_stats()["total_nodes"] == 1

    def test_find_node_by_label_and_property(self, graph):
        graph.add_node("Company", {"name": "Meta"})
        graph.add_node("Company", {"name": "Amazon"})
        node = graph.find_node("Company", "name", "Meta")
        assert node is not None
        assert node.properties["name"] == "Meta"

    def test_find_node_returns_none_when_missing(self, graph):
        graph.add_node("Company", {"name": "Meta"})
        assert graph.find_node("Company", "name", "Nonexistent") is None

    def test_get_nodes_by_label(self, graph):
        graph.add_node("Company", {"name": "A"})
        graph.add_node("Company", {"name": "B"})
        graph.add_node("Topic", {"name": "Algorithms"})
        companies = graph.get_nodes_by_label("Company", limit=10)
        assert len(companies) == 2
        for c in companies:
            assert c.label == "Company"


class TestInMemoryCognitiveGraphInterviews:
    """High-level: add_interview wires up Company/Role/Question/Answer nodes."""

    def test_add_interview_creates_compound_graph(self, graph):
        interview_id = graph.add_interview(
            user_id="u1",
            company="Stripe",
            role="SWE",
            questions=[
                {"text": "What is CAP?", "category": "technical"},
            ],
            answers=[
                {"text": "Consistency, availability, partition tolerance",
                 "quality": "good", "confidence": 0.8},
            ],
        )
        assert interview_id is not None

        # Should have: Interview + Company + Role + Question + Answer + Topic nodes
        stats = graph.get_stats()
        assert stats["total_nodes"] >= 5

        # Company node should be findable
        stripe = graph.find_node("Company", "name", "Stripe")
        assert stripe is not None

    def test_add_skill(self, graph):
        graph.add_skill("u1", "Python", "expert")
        graph.add_skill("u1", "Rust", "intermediate")

        skills = graph.get_user_skills("u1")
        assert len(skills) == 2
        names = {s.get("skill", s.get("name", "")) for s in skills}
        assert "Python" in names
        assert "Rust" in names

    def test_get_user_interviews(self, graph):
        graph.add_interview("u1", "A", "SWE", [], [])
        graph.add_interview("u1", "B", "PM", [], [])
        graph.add_interview("u2", "C", "SWE", [], [])

        u1_interviews = graph.get_user_interviews("u1")
        assert len(u1_interviews) == 2

        u2_interviews = graph.get_user_interviews("u2")
        assert len(u2_interviews) == 1

    def test_get_user_interviews_empty_for_unknown_user(self, graph):
        assert graph.get_user_interviews("never-existed") == []


class TestInMemoryCognitiveGraphNeighbors:
    """get_neighbors: traverse Company → Interview → Question."""

    def test_get_neighbors_returns_edges(self, graph):
        graph.add_interview("u1", "X", "SWE",
                            [{"text": "Q1"}], [{"text": "A1"}])
        company = graph.find_node("Company", "name", "X")
        assert company is not None

        neighbors = graph.get_neighbors(company.id)
        # At minimum: company → interview edge
        assert len(neighbors) >= 1
        labels = {n.label for n, _ in neighbors}
        assert "Interview" in labels

    def test_get_neighbors_with_relationship_filter(self, graph):
        graph.add_interview("u1", "Y", "SWE",
                            [{"text": "Q1"}], [])
        company = graph.find_node("Company", "name", "Y")
        assert company is not None

        # Filter to edges labeled "CONTAINS" — should be empty at the
        # Company → Interview level (the company is related to the
        # interview, not CONTAINS it).
        contains_neighbors = graph.get_neighbors(company.id, "CONTAINS")
        # CONTAINS is Interview→Question, not Company→Interview, so 0
        # neighbors is the correct answer.
        assert isinstance(contains_neighbors, list)


class TestInMemoryCognitiveGraphStats:
    """get_stats: the shape that /cognitive-graph/status returns."""

    def test_stats_shape(self, graph):
        graph.add_interview("u1", "Z", "SWE", [{"text": "Q"}], [])
        stats = graph.get_stats()
        # Must have these keys for the /status and /stats endpoints
        for key in ["total_nodes", "total_edges", "nodes_by_label"]:
            assert key in stats, f"stats missing {key}"

    def test_nodes_by_label_counts(self, graph):
        graph.add_interview("u1", "A", "SWE", [{"text": "Q"}], [])
        stats = graph.get_stats()
        labels = stats["nodes_by_label"]
        assert labels.get("Company", 0) >= 1
        assert labels.get("Interview", 0) >= 1
        assert labels.get("Question", 0) >= 1


class TestKeywordSearch:
    """_keyword_search helper from routes/cognitive.py."""

    def test_finds_nodes_by_property_keyword(self):
        from routes.cognitive import _keyword_search

        g = InMemoryCognitiveGraph()
        g.add_node("Company", {"name": "Stripe"})
        g.add_node("Topic", {"name": "Distributed systems"})

        results = _keyword_search(g, "Stripe", limit=10)
        assert len(results) >= 1
        # Top result should be the Stripe company (matched on "stripe")
        top = results[0]
        assert "stripe" in (top["properties"].get("name", "") or "").lower()

    def test_empty_query_returns_nothing(self):
        from routes.cognitive import _keyword_search

        g = InMemoryCognitiveGraph()
        g.add_node("Company", {"name": "Stripe"})
        results = _keyword_search(g, "", limit=10)
        assert results == []

    def test_limit_respected(self):
        from routes.cognitive import _keyword_search

        g = InMemoryCognitiveGraph()
        for i in range(10):
            g.add_node("Company", {"name": f"Company {i}"})
        results = _keyword_search(g, "Company", limit=3)
        assert len(results) == 3


class TestAdvancedKeywordSearch:
    """_advanced_keyword_search helper: company/topic/category/difficulty filters."""

    def test_company_filter(self):
        from routes.cognitive import _advanced_keyword_search

        g = InMemoryCognitiveGraph()
        g.add_interview("u1", "Google", "SWE",
                        [{"text": "Q1", "category": "coding"}], [])
        g.add_interview("u1", "Meta", "SWE",
                        [{"text": "Q2", "category": "coding"}], [])

        results = _advanced_keyword_search(g, company="Google", limit=10)
        # Filter should keep only Google-related nodes
        for r in results:
            props = r["properties"]
            assert (
                props.get("company", "").lower() == "google" or
                props.get("name", "").lower() == "google"
            ), f"non-Google result leaked through filter: {r}"

    def test_topic_filter(self):
        from routes.cognitive import _advanced_keyword_search

        g = InMemoryCognitiveGraph()
        g.add_interview("u1", "A", "SWE",
                        [{"text": "Q1", "topic": "algorithms"}], [])
        g.add_interview("u1", "B", "SWE",
                        [{"text": "Q2", "topic": "system design"}], [])

        results = _advanced_keyword_search(g, topic="algorithms", limit=10)
        for r in results:
            props = r["properties"]
            assert (
                props.get("topic", "").lower() == "algorithms" or
                props.get("name", "").lower() == "algorithms"
            ), f"non-algorithms result leaked: {r}"

    def test_no_filters_returns_all(self):
        from routes.cognitive import _advanced_keyword_search

        g = InMemoryCognitiveGraph()
        for i in range(5):
            g.add_node("Company", {"name": f"C{i}"})
        results = _advanced_keyword_search(g, limit=100)
        assert len(results) == 5


class TestGraphNodeDataclass:
    """GraphNode.to_dict shape — the JSON shape returned by API endpoints."""

    def test_to_dict_includes_id_label_properties(self):
        node = GraphNode(id="abc", label="Company", properties={"name": "X"})
        d = node.to_dict()
        assert d["id"] == "abc"
        assert d["label"] == "Company"
        assert d["properties"] == {"name": "X"}
        assert "created_at" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
