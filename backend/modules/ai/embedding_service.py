"""
Embedding Service for AI Note Taker
Provides sentence embeddings using sentence-transformers for semantic search,
entity matching, and similarity comparison.

Follows the whisper_handler.py pattern: lazy init, thread lock, warmup thread,
device auto-detection, and graceful fallback.
"""

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("embedding_service")

# ==============================
# GLOBAL CONFIG
# ==============================

DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_DEVICE = "auto"
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 output dimension
CACHE_DIR = Path(__file__).parent.parent / "platform" / "data" / "vectors"
CACHE_FILE = CACHE_DIR / "embedding_cache.json"
MAX_CACHE_SIZE = 10000

# ==============================
# AVAILABILITY FLAG
# ==============================

EMBEDDING_AVAILABLE = False  # Set True after successful model load

# ==============================
# SINGLETON
# ==============================

_service: Optional["EmbeddingService"] = None
_service_lock = threading.Lock()
_service_ready = threading.Event()


class EmbeddingService:
    """Sentence embedding service using sentence-transformers."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        cache_size: int = MAX_CACHE_SIZE,
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._cache: Dict[str, List[float]] = {}
        self._cache_lock = threading.Lock()
        self._max_cache = cache_size
        self._index_built = False

        # Load persisted cache
        self._load_cache()

    def _load_model(self):
        """Lazy-load the sentence-transformer model."""
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        logger.info("[EmbeddingService] Loading model: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name, device=self.device)
        logger.info("[EmbeddingService] Model loaded successfully")

    def _load_cache(self):
        """Load embedding cache from disk."""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r") as f:
                    self._cache = json.load(f)
                logger.info("[EmbeddingService] Loaded %d cached embeddings", len(self._cache))
        except Exception as e:
            logger.warning("[EmbeddingService] Failed to load cache: %s", str(e))
            self._cache = {}

    def _save_cache(self):
        """Persist embedding cache to disk."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning("[EmbeddingService] Failed to save cache: %s", str(e))

    @staticmethod
    def _hash_text(text: str) -> str:
        """Hash text for cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def embed(self, text: str) -> List[float]:
        """Embed a single text string. Returns a 384-dim float vector."""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION

        text = text.strip()
        cache_key = self._hash_text(text)

        # Check cache
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Compute embedding
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        result = embedding.tolist()

        # Cache result
        with self._cache_lock:
            if len(self._cache) >= self._max_cache:
                # Evict oldest 20% of entries
                keys_to_remove = list(self._cache.keys())[: self._max_cache // 5]
                for k in keys_to_remove:
                    del self._cache[k]
            self._cache[cache_key] = result

        return result

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in one forward pass. More efficient than per-item."""
        if not texts:
            return []

        # Separate cached and uncached
        cached_results: Dict[int, List[float]] = {}
        uncached_texts: List[str] = []
        uncached_indices: List[int] = []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                cached_results[i] = [0.0] * EMBEDDING_DIMENSION
                continue

            text = text.strip()
            cache_key = self._hash_text(text)

            with self._cache_lock:
                if cache_key in self._cache:
                    cached_results[i] = self._cache[cache_key]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)

        # Batch encode uncached texts
        if uncached_texts:
            self._load_model()
            embeddings = self._model.encode(
                uncached_texts, convert_to_numpy=True, normalize_embeddings=True
            )

            for j, (idx, text) in enumerate(zip(uncached_indices, uncached_texts)):
                result = embeddings[j].tolist()
                cache_key = self._hash_text(text)

                with self._cache_lock:
                    self._cache[cache_key] = result
                cached_results[idx] = result

        # Assemble in order
        return [cached_results[i] for i in range(len(texts))]

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts."""
        emb_a = np.array(self.embed(text_a))
        emb_b = np.array(self.embed(text_b))

        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(emb_a, emb_b) / (norm_a * norm_b))

    def find_most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Tuple[int, float]]:
        """
        Find the top-k most similar candidates to the query.

        Returns list of (index, score) tuples sorted by score descending.
        Only includes candidates above the threshold.
        """
        if not candidates:
            return []

        query_emb = np.array(self.embed(query))
        candidate_embs = np.array(self.embed_batch(candidates))

        # Compute cosine similarities
        query_norm = np.linalg.norm(query_emb)
        if query_norm == 0:
            return []

        # Normalize query
        query_emb = query_emb / query_norm

        # Compute candidate norms
        candidate_norms = np.linalg.norm(candidate_embs, axis=1)
        # Avoid division by zero
        candidate_norms[candidate_norms == 0] = 1.0
        normalized_candidates = candidate_embs / candidate_norms[:, np.newaxis]

        # Dot product = cosine similarity (since both are normalized)
        similarities = np.dot(normalized_candidates, query_emb)

        # Filter by threshold and sort
        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                results.append((idx, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# ==============================
# MODULE-LEVEL API
# ==============================


def get_embedding_service() -> Optional[EmbeddingService]:
    """Thread-safe lazy singleton getter for EmbeddingService."""
    global _service, EMBEDDING_AVAILABLE

    if not EMBEDDING_AVAILABLE:
        return None

    if _service is None:
        with _service_lock:
            if _service is None:
                try:
                    _service = EmbeddingService()
                    EMBEDDING_AVAILABLE = True
                except Exception as e:
                    logger.error("[EmbeddingService] Failed to initialize: %s", str(e))
                    EMBEDDING_AVAILABLE = False
                    return None

    return _service


def warmup():
    """Preload model at startup in a background thread."""
    global EMBEDDING_AVAILABLE

    try:
        logger.info("[EmbeddingService] Warming up...")
        service = get_embedding_service()
        if service:
            # Force model load by embedding a test string
            service.embed("warmup test")
            EMBEDDING_AVAILABLE = True
            logger.info("[EmbeddingService] Ready")
        else:
            EMBEDDING_AVAILABLE = False
    except Exception as e:
        logger.warning("[EmbeddingService] Warmup failed: %s", str(e))
        EMBEDDING_AVAILABLE = False
    finally:
        _service_ready.set()


def wait_for_service(timeout: float = 60) -> bool:
    """Block until the embedding service is ready (or timeout expires)."""
    return _service_ready.wait(timeout=timeout)


def save_cache():
    """Save the embedding cache to disk. Call on shutdown."""
    if _service:
        _service._save_cache()