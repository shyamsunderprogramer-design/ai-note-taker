"""Zero-config in-memory cognitive graph — no Neo4j required.

Drop-in replacement for the Neo4j-backed cognitive_graph module.
Uses dictionaries and sets to build a lightweight knowledge graph
that persists for the process lifetime.

Falls back to Neo4j when available, but works standalone.
"""
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("cognitive_graph_memory")

# ─── Data structures ────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A node in the cognitive graph."""
    id: str
    label: str  # Interview, Question, Answer, Company, Role, Topic, Skill, User
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"id": self.id, "label": self.label, "properties": self.properties, "created_at": self.created_at}


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""
    id: str
    source_id: str
    target_id: str
    relationship: str  # CONTAINS, ASKED_BY, ANSWERED_WITH, RELATED_TO, FOR_ROLE, etc.
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {"id": self.id, "source": self.source_id, "target": self.target_id,
                "relationship": self.relationship, "properties": self.properties}


class InMemoryCognitiveGraph:
    """Zero-config cognitive graph using in-memory storage.

    Provides the same interface as the Neo4j-backed version but
    requires no external database or configuration.
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._label_index: Dict[str, Set[str]] = defaultdict(set)  # label -> node_ids
        self._outgoing: Dict[str, List[str]] = defaultdict(list)    # node_id -> edge_ids
        self._incoming: Dict[str, List[str]] = defaultdict(list)    # node_id -> edge_ids
        self._prop_index: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

        logger.info("[MemoryGraph] Zero-config cognitive graph initialized")

    # ─── Node operations ────────────────────────────────────────────────

    def add_node(self, label: str, properties: Dict[str, Any] = None, node_id: str = None) -> str:
        """Add a node to the graph. Returns the node ID."""
        nid = node_id or str(uuid.uuid4())[:8]

        # Dedup: if a node with the same label and unique key exists, return it
        if "name" in (properties or {}):
            existing = self.find_node(label, "name", properties["name"])
            if existing:
                return existing.id

        node = GraphNode(id=nid, label=label, properties=properties or {})
        self._nodes[nid] = node
        self._label_index[label].add(nid)

        # Index searchable properties
        for key, value in (properties or {}).items():
            if isinstance(value, str):
                self._prop_index[label][f"{key}={value.lower()}"].add(nid)

        return nid

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def find_node(self, label: str, prop_key: str, prop_value: str) -> Optional[GraphNode]:
        """Find a node by label and property value."""
        index_key = f"{prop_key}={prop_value.lower()}"
        node_ids = self._prop_index.get(label, {}).get(index_key, set())
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node:
                return node
        return None

    def get_nodes_by_label(self, label: str, limit: int = 100) -> List[GraphNode]:
        """Get all nodes with a given label."""
        nids = list(self._label_index.get(label, set()))[:limit]
        return [self._nodes[nid] for nid in nids if nid in self._nodes]

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update a node's properties."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.properties.update(properties)
        return True

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its connected edges."""
        if node_id not in self._nodes:
            return False

        # Remove connected edges
        edge_ids = self._outgoing.get(node_id, []) + self._incoming.get(node_id, [])
        for eid in edge_ids:
            self._edges.pop(eid, None)

        # Clean indices
        node = self._nodes.pop(node_id)
        self._label_index.get(node.label, set()).discard(node_id)
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)

        return True

    # ─── Edge operations ────────────────────────────────────────────────

    def add_edge(self, source_id: str, target_id: str, relationship: str,
                 properties: Dict[str, Any] = None) -> Optional[str]:
        """Add a directed edge. Returns edge ID or None if nodes don't exist."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        # Avoid duplicate edges
        for eid in self._outgoing.get(source_id, []):
            edge = self._edges.get(eid)
            if edge and edge.target_id == target_id and edge.relationship == relationship:
                return eid

        eid = str(uuid.uuid4())[:8]
        edge = GraphEdge(id=eid, source_id=source_id, target_id=target_id,
                         relationship=relationship, properties=properties or {})
        self._edges[eid] = edge
        self._outgoing[source_id].append(eid)
        self._incoming[target_id].append(eid)
        return eid

    def get_neighbors(self, node_id: str, relationship: str = None,
                      direction: str = "both") -> List[Tuple[GraphNode, GraphEdge]]:
        """Get neighboring nodes connected by edges."""
        results = []

        if direction in ("outgoing", "both"):
            for eid in self._outgoing.get(node_id, []):
                edge = self._edges.get(eid)
                if edge and (not relationship or edge.relationship == relationship):
                    target = self._nodes.get(edge.target_id)
                    if target:
                        results.append((target, edge))

        if direction in ("incoming", "both"):
            for eid in self._incoming.get(node_id, []):
                edge = self._edges.get(eid)
                if edge and (not relationship or edge.relationship == relationship):
                    source = self._nodes.get(edge.source_id)
                    if source:
                        results.append((source, edge))

        return results

    # ─── High-level operations ──────────────────────────────────────────

    def add_interview(self, user_id: str, company: str, role: str,
                      questions: List[Dict], answers: List[Dict]) -> str:
        """Record an interview session in the graph."""
        # Create/merge nodes
        user_nid = self.add_node("User", {"name": user_id})
        company_nid = self.add_node("Company", {"name": company})
        role_nid = self.add_node("Role", {"name": role})
        interview_nid = self.add_node("Interview", {
            "company": company, "role": role, "date": datetime.now().isoformat(),
            "question_count": len(questions),
        })

        # Connect
        self.add_edge(user_nid, interview_nid, "CONDUCTED")
        self.add_edge(interview_nid, company_nid, "AT_COMPANY")
        self.add_edge(interview_nid, role_nid, "FOR_ROLE")

        # Add questions and answers
        for i, q in enumerate(questions):
            topic = q.get("topic", "general")
            topic_nid = self.add_node("Topic", {"name": topic})
            q_nid = self.add_node("Question", {"text": q.get("text", ""), "category": q.get("category", "")})
            self.add_edge(interview_nid, q_nid, "CONTAINS")
            self.add_edge(q_nid, topic_nid, "ABOUT")

            if i < len(answers):
                a = answers[i]
                a_nid = self.add_node("Answer", {
                    "text": a.get("text", ""),
                    "quality": a.get("quality", "unknown"),
                    "confidence": a.get("confidence", 0.0),
                })
                self.add_edge(q_nid, a_nid, "ANSWERED_WITH")

        logger.info("[MemoryGraph] Recorded interview: %s @ %s for %s (%d questions)",
                     interview_nid, company, role, len(questions))
        return interview_nid

    def add_skill(self, user_id: str, skill_name: str, proficiency: str = "intermediate"):
        """Add a skill node connected to a user."""
        user_nid = self.add_node("User", {"name": user_id})
        skill_nid = self.add_node("Skill", {"name": skill_name, "proficiency": proficiency})
        self.add_edge(user_nid, skill_nid, "HAS_SKILL")

    def get_user_skills(self, user_id: str) -> List[Dict]:
        """Get all skills for a user."""
        user_nid = self.find_node("User", "name", user_id)
        if not user_nid:
            return []
        neighbors = self.get_neighbors(user_nid.id, "HAS_SKILL")
        return [{"skill": n.properties.get("name", ""), "proficiency": n.properties.get("proficiency", "")}
                for n, _ in neighbors]

    def get_user_interviews(self, user_id: str) -> List[Dict]:
        """Get all interviews for a user."""
        user_nid = self.find_node("User", "name", user_id)
        if not user_nid:
            return []
        neighbors = self.get_neighbors(user_nid.id, "CONDUCTED")
        return [n.to_dict() for n, _ in neighbors]

    def find_related_topics(self, topic_name: str, depth: int = 2) -> List[Dict]:
        """Find topics related to a given topic within depth hops."""
        topic_nid = self.find_node("Topic", "name", topic_name)
        if not topic_nid:
            return []

        visited = set()
        results = []
        queue = [(topic_nid.id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_id in visited or current_depth > depth:
                continue
            visited.add(current_id)

            node = self._nodes.get(current_id)
            if node and node.id != topic_nid.id:
                results.append(node.to_dict())

            for neighbor, edge in self.get_neighbors(current_id):
                if neighbor.id not in visited:
                    queue.append((neighbor.id, current_depth + 1))

        return results

    def get_knowledge_graph(self, user_id: str = None, limit: int = 50) -> Dict:
        """Export the graph as a dict of nodes and edges for visualization."""
        nodes = []
        edges = []

        if user_id:
            # Get user's subgraph
            user_nid = self.find_node("User", "name", user_id)
            if user_nid:
                visited = set()
                queue = [user_nid.id]
                while queue and len(nodes) < limit:
                    nid = queue.pop(0)
                    if nid in visited:
                        continue
                    visited.add(nid)
                    node = self._nodes.get(nid)
                    if node:
                        nodes.append(node.to_dict())
                        for neighbor, edge in self.get_neighbors(nid):
                            if neighbor.id not in visited:
                                queue.append(neighbor.id)
                            if edge.id not in [e["id"] for e in edges]:
                                edges.append(edge.to_dict())
        else:
            for node in list(self._nodes.values())[:limit]:
                nodes.append(node.to_dict())
            for edge in list(self._edges.values())[:limit]:
                edges.append(edge.to_dict())

        return {"nodes": nodes, "edges": edges}

    # ─── Stats ──────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        label_counts = {label: len(nids) for label, nids in self._label_index.items()}
        rel_counts = defaultdict(int)
        for edge in self._edges.values():
            rel_counts[edge.relationship] += 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_label": dict(label_counts),
            "edges_by_relationship": dict(rel_counts),
            "backend": "in_memory",
        }


# ─── Singleton instance ─────────────────────────────────────────────────────

memory_graph = InMemoryCognitiveGraph()


# ─── Compatibility layer ────────────────────────────────────────────────────
# Provides the same interface as the Neo4j-backed cognitive_graph module

def get_cognitive_graph():
    """Get the best available cognitive graph backend.

    Returns the Neo4j-backed graph if Neo4j is available and configured,
    otherwise returns the in-memory zero-config graph.
    """
    try:
        from cognitive_graph import CognitiveGraph
        neo4j_graph = CognitiveGraph()
        if neo4j_graph.is_available():
            return neo4j_graph
    except Exception:
        pass  # nosec B110 — optional Neo4j fallback

    return memory_graph