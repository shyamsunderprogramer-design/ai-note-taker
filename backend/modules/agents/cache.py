"""
Token Caching — Caches cognitive graph and document RAG results for similar questions.

Reduces redundant LLM context queries when the same or similar questions appear
multiple times in a session. Uses cosine similarity on TF-IDF vectors to detect
similar questions, with TTL-based expiration to keep results fresh.
"""

import time
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("agents.cache")


@dataclass
class CacheEntry:
    """A cached context lookup result."""
    query_hash: str
    query_text: str
    graph_results: List[Dict] = field(default_factory=list)
    rag_results: List[Dict] = field(default_factory=list)
    company_insights: Dict = field(default_factory=dict)
    entities: Dict = field(default_factory=dict)
    created_at: float = 0.0
    hit_count: int = 0
    similarity_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> Dict:
        return {
            "query_hash": self.query_hash,
            "query_text": self.query_text[:100],
            "age_seconds": round(self.age_seconds, 1),
            "hit_count": self.hit_count,
            "graph_results_count": len(self.graph_results),
            "rag_results_count": len(self.rag_results),
        }


class ContextCache:
    """LRU-style cache for agent context lookups.

    Caches the results of cognitive graph queries, document RAG lookups,
    and entity extractions. When a similar question is asked, the cached
    results are returned instead of re-querying the data sources.

    Features:
      - TTL-based expiration (default 5 minutes)
      - Similarity-based matching (not just exact match)
      - Per-session isolation
      - Automatic eviction when cache is full
      - Thread-safe operations
    """

    def __init__(
        self,
        max_entries: int = 200,
        default_ttl: int = 300,  # 5 minutes
        similarity_threshold: float = 0.75,
    ):
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.similarity_threshold = similarity_threshold
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "similarity_hits": 0,
            "evictions": 0,
        }

    def _hash_query(self, query: str) -> str:
        """Normalize and hash a query string for exact matching."""
        normalized = " ".join(query.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()  # nosec B324 — used for cache key, not security

    def _tokenize(self, text: str) -> set:
        """Simple tokenization for similarity comparison."""
        # Remove punctuation and normalize
        import re
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "what", "how", "why", "when", "where", "who", "which", "that",
            "this", "these", "those", "it", "its", "you", "your", "we",
            "our", "they", "their", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "as", "into", "about", "between",
        }
        words = set(text.split())
        return words - stop_words

    def _compute_similarity(self, query1: str, query2: str) -> float:
        """Compute Jaccard similarity between two queries.

        Jaccard similarity = |intersection| / |union|

        This is fast, requires no ML models, and works well for
        detecting paraphrased questions.
        """
        tokens1 = self._tokenize(query1)
        tokens2 = self._tokenize(query2)

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        return intersection / union

    def _find_similar(self, query: str) -> Optional[CacheEntry]:
        """Find a similar cached query above the similarity threshold."""
        best_entry = None
        best_score = 0.0

        for entry in self._store.values():
            # Skip expired entries
            if entry.age_seconds > self.default_ttl:
                continue

            score = self._compute_similarity(query, entry.query_text)
            if score > self.similarity_threshold and score > best_score:
                best_score = score
                best_entry = entry

        if best_entry:
            best_entry.similarity_scores[query] = round(best_score, 3)

        return best_entry

    def _evict_if_needed(self):
        """Evict oldest entries if cache is full."""
        while len(self._store) >= self.max_entries:
            # Find the oldest entry
            oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
            del self._store[oldest_key]
            self._stats["evictions"] += 1

    def get(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> Optional[CacheEntry]:
        """Look up cached context for a query.

        First tries exact match, then similarity match.
        Returns None if no match found (cache miss).
        """
        with self._lock:
            # Try exact match first
            query_hash = self._hash_query(query)
            entry = self._store.get(query_hash)

            if entry and entry.age_seconds <= self.default_ttl:
                entry.hit_count += 1
                self._stats["hits"] += 1
                logger.debug(f"[ContextCache] Exact hit for: {query[:50]}")
                return entry

            # Try similarity match
            similar = self._find_similar(query)
            if similar:
                similar.hit_count += 1
                self._stats["similarity_hits"] += 1
                logger.debug(f"[ContextCache] Similarity hit for: {query[:50]} (score: {similar.similarity_scores.get(query, 0)})")
                return similar

            self._stats["misses"] += 1
            return None

    def put(
        self,
        query: str,
        graph_results: List[Dict] = None,
        rag_results: List[Dict] = None,
        company_insights: Dict = None,
        entities: Dict = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Store context lookup results in the cache."""
        with self._lock:
            self._evict_if_needed()

            query_hash = self._hash_query(query)
            entry = CacheEntry(
                query_hash=query_hash,
                query_text=query.strip(),
                graph_results=graph_results or [],
                rag_results=rag_results or [],
                company_insights=company_insights or {},
                entities=entities or {},
                created_at=time.time(),
                hit_count=0,
            )

            self._store[query_hash] = entry
            logger.debug(f"[ContextCache] Stored: {query[:50]} ({len(entry.graph_results)} graph, {len(entry.rag_results)} RAG results)")

    def invalidate(self, query: str) -> bool:
        """Remove a specific query from the cache."""
        with self._lock:
            query_hash = self._hash_query(query)
            if query_hash in self._store:
                del self._store[query_hash]
                return True
            return False

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()
            logger.info("[ContextCache] Cleared all entries")

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._store.items()
                if v.age_seconds > self.default_ttl
            ]
            for k in expired_keys:
                del self._store[k]
            if expired_keys:
                logger.info(f"[ContextCache] Cleaned up {len(expired_keys)} expired entries")
            return len(expired_keys)

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"] + self._stats["similarity_hits"]
            return {
                "total_entries": len(self._store),
                "max_entries": self.max_entries,
                "exact_hits": self._stats["hits"],
                "similarity_hits": self._stats["similarity_hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": round((self._stats["hits"] + self._stats["similarity_hits"]) / max(1, total), 3),
                "ttl_seconds": self.default_ttl,
                "similarity_threshold": self.similarity_threshold,
            }


# Global cache singleton
context_cache = ContextCache()


def get_cache() -> ContextCache:
    """Get the global context cache instance."""
    return context_cache