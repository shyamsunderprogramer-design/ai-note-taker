"""
Semantic Search Mixin for AI Note Taker
Replaces CONTAINS-based Cypher queries with embedding similarity search.

When EmbeddingService is available, queries are semantically matched
against node embeddings. Falls back to original keyword Cypher search
when embeddings are unavailable.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger("semantic_search")

# Persistence path
EMBEDDINGS_DIR = Path(__file__).parent.parent / "platform" / "data" / "vectors"
GRAPH_EMBEDDINGS_FILE = EMBEDDINGS_DIR / "graph_embeddings.json"


class SemanticSearchMixin:
    """Adds semantic search capabilities to CognitiveGraph using embeddings."""

    def __init__(self, embedding_service=None, neo4j_driver=None):
        """
        Args:
            embedding_service: EmbeddingService instance (lazy init ok)
            neo4j_driver: Neo4j driver for fetching nodes
        """
        self._embedding_service = embedding_service
        self._neo4j_driver = neo4j_driver
        self._node_embeddings: Dict[str, List[float]] = {}  # node_id -> embedding
        self._node_texts: Dict[str, str] = {}  # node_id -> text
        self._node_types: Dict[str, str] = {}  # node_id -> type
        self._index_built = False
        self._similarity_threshold = 0.3
        self._build_lock = threading.Lock()

    def _get_embedding_service(self):
        """Lazily get the embedding service."""
        if self._embedding_service is None:
            try:
                from modules.ai.embedding_service import get_embedding_service, EMBEDDING_AVAILABLE
                if EMBEDDING_AVAILABLE:
                    self._embedding_service = get_embedding_service()
            except Exception as e:
                logger.debug("[SemanticSearch] Embedding service unavailable: %s", str(e))
        return self._embedding_service

    def _load_persisted_embeddings(self):
        """Load previously computed embeddings from disk."""
        try:
            if GRAPH_EMBEDDINGS_FILE.exists():
                with open(GRAPH_EMBEDDINGS_FILE, "r") as f:
                    data = json.load(f)
                self._node_embeddings = data.get("embeddings", {})
                self._node_texts = data.get("texts", {})
                self._node_types = data.get("types", {})
                logger.info("[SemanticSearch] Loaded %d persisted embeddings", len(self._node_embeddings))
                return len(self._node_embeddings) > 0
        except Exception as e:
            logger.warning("[SemanticSearch] Failed to load persisted embeddings: %s", str(e))
        return False

    def _persist_embeddings(self):
        """Save computed embeddings to disk."""
        try:
            EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "embeddings": self._node_embeddings,
                "texts": self._node_texts,
                "types": self._node_types,
            }
            with open(GRAPH_EMBEDDINGS_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning("[SemanticSearch] Failed to persist embeddings: %s", str(e))

    def _build_index(self):
        """Fetch all nodes from Neo4j and compute embeddings. Called once on first search."""
        with self._build_lock:
            if self._index_built:
                return True

            # Try loading from disk first
            if self._load_persisted_embeddings():
                self._index_built = True
                return True

            service = self._get_embedding_service()
            if not service or not self._neo4j_driver:
                logger.info("[SemanticSearch] No embedding service or Neo4j driver, skipping index build")
                return False

            try:
                # Fetch all searchable nodes from Neo4j
                node_queries = {
                    "Question": "MATCH (q:Question) RETURN q.id as id, q.text as text, q.category as category",
                    "Topic": "MATCH (t:Topic) RETURN t.id as id, t.name as text, 'topic' as category",
                    "Skill": "MATCH (s:Skill) RETURN s.id as id, s.name as text, s.category as category",
                    "Company": "MATCH (c:Company) RETURN c.id as id, c.name as text, 'company' as category",
                }

                all_texts = []
                all_ids = []
                all_types = {}

                with self._neo4j_driver.session() as session:
                    for node_type, query in node_queries.items():
                        try:
                            result = session.run(query)
                            for record in result:
                                node_id = record.get("id", "")
                                text = record.get("text", "")
                                if node_id and text:
                                    all_ids.append(node_id)
                                    all_texts.append(text)
                                    all_types[node_id] = node_type
                                    self._node_types[node_id] = node_type
                                    self._node_texts[node_id] = text
                        except Exception as e:
                            logger.debug("[SemanticSearch] Failed to fetch %s nodes: %s", node_type, e)

                if not all_texts:
                    logger.info("[SemanticSearch] No nodes found in Neo4j")
                    self._index_built = True
                    return True

                # Batch embed all texts
                embeddings = service.embed_batch(all_texts)
                for node_id, embedding in zip(all_ids, embeddings):
                    self._node_embeddings[node_id] = embedding

                self._persist_embeddings()
                self._index_built = True
                logger.info("[SemanticSearch] Built index with %d nodes", len(all_ids))
                return True

            except Exception as e:
                logger.error("[SemanticSearch] Failed to build index: %s", str(e))
                return False

    def _index_node(self, node_type: str, node_id: str, text: str):
        """Compute and cache embedding for a newly added graph node."""
        service = self._get_embedding_service()
        if not service:
            return

        try:
            embedding = service.embed(text)
            self._node_embeddings[node_id] = embedding
            self._node_texts[node_id] = text
            self._node_types[node_id] = node_type
        except Exception as e:
            logger.debug("[SemanticSearch] Failed to index node %s: %s", node_id, e)

    def semantic_search(self, query: str, limit: int = 10, driver=None) -> List[Dict]:
        """
        Search using embedding similarity. Falls back to Cypher CONTAINS search
        if EmbeddingService is unavailable.

        Returns results in the same format as CognitiveGraph.semantic_search().
        """
        # Build index on first search
        if not self._index_built:
            if driver and not self._neo4j_driver:
                self._neo4j_driver = driver
            if not self._build_index():
                return []  # No index, no results

        service = self._get_embedding_service()
        if not service:
            return []

        # Embed the query
        query_emb = np.array(service.embed(query))
        if np.linalg.norm(query_emb) == 0:
            return []

        # Compute similarity against all node embeddings
        node_ids = list(self._node_embeddings.keys())
        if not node_ids:
            return []

        embeddings_matrix = np.array([self._node_embeddings[nid] for nid in node_ids])
        norms = np.linalg.norm(embeddings_matrix, axis=1)
        norms[norms == 0] = 1.0  # avoid division by zero
        normalized = embeddings_matrix / norms[:, np.newaxis]

        query_norm = query_emb / np.linalg.norm(query_emb)
        similarities = np.dot(normalized, query_norm)

        # Filter by threshold and sort
        scored_results = []
        for idx, (nid, score) in enumerate(zip(node_ids, similarities)):
            if score >= self._similarity_threshold:
                scored_results.append((nid, float(score)))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_results[:limit]

        # Format results to match Cypher search output
        formatted = []
        for node_id, relevance in top_results:
            node_type = self._node_types.get(node_id, "Unknown")
            text = self._node_texts.get(node_id, "")
            formatted.append({
                "node_id": node_id,
                "node_type": node_type,
                "text": text,
                "relevance": round(relevance, 3),
                "query": query,
            })

        return formatted

    def _fallback_search(self, query: str, limit: int, driver) -> List[Dict]:
        """
        Original Cypher CONTAINS-based search. Used when embeddings are unavailable.
        This is the existing semantic_search() method from cognitive_graph.py.
        """
        if not driver:
            return []

        cypher = """
        // Search across multiple fields with scoring
        CALL {
            // Search in question text
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE q.text CONTAINS $keyword
            WITH q, a, 10 as score
            RETURN q, a, score
            UNION
            // Search in answer text
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE a.text CONTAINS $keyword
            WITH q, a, 8 as score
            RETURN q, a, score
            UNION
            // Search in transcript
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE a.transcript CONTAINS $keyword
            WITH q, a, 6 as score
            RETURN q, a, score
            UNION
            // Search by topic
            MATCH (t:Topic)
            WHERE t.name CONTAINS $keyword
            MATCH (t)<-[:RELATED_TO]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WITH q, a, 9 as score
            RETURN q, a, score
            UNION
            // Search by company
            MATCH (c:Company)
            WHERE c.name CONTAINS $keyword
            MATCH (c)<-[:ASKED_BY]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WITH q, a, 7 as score
            RETURN q, a, score
            UNION
            // Search by skill
            MATCH (s:Skill)
            WHERE s.name CONTAINS $keyword
            MATCH (s)<-[:DEMONSTRATES]-(a:Answer)<-[:ANSWERED_WITH]-(q:Question)
            WITH q, a, 8 as score
            RETURN q, a, score
        }
        WITH q, a, max(score) as relevance
        ORDER BY relevance DESC
        LIMIT $limit
        OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
        OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
        OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
        RETURN DISTINCT q.id as question_id,
               q.text as question,
               a.text as answer,
               q.category as category,
               q.difficulty as difficulty,
               collect(DISTINCT t.name) as topics,
               c.name as company,
               i.timestamp as date,
               relevance
        ORDER BY relevance DESC
        """

        try:
            with driver.session() as session:
                result = session.run(cypher, keyword=query.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error("[SemanticSearch] Fallback search failed: %s", str(e))
            return []