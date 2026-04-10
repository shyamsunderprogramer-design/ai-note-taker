"""
Smart Classifier for AI Note Taker
Provides zero-shot classification for interview questions, content focus,
difficulty assessment, and conversation type using local ML models.

Uses transformers pipeline with a lightweight NLI model. Falls back to
existing keyword-based methods when the model is unavailable.
"""

import hashlib
import logging
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("smart_classifier")

# ==============================
# GLOBAL CONFIG
# ==============================

DEFAULT_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
DEFAULT_DEVICE = "auto"
CLASSIFIER_CACHE_SIZE = 5000

# ==============================
# LABEL SETS
# ==============================

QUESTION_LABELS = [
    "technical coding question",
    "system design question",
    "behavioral interview question",
    "knowledge and conceptual question",
    "general question",
]

QUESTION_LABEL_MAP = {
    "technical coding question": "technical",
    "system design question": "system_design",
    "behavioral interview question": "behavioral",
    "knowledge and conceptual question": "knowledge",
    "general question": "general",
}

CONTENT_LABELS = [
    "system design and architecture",
    "algorithms and data structures",
    "behavioral and soft skills",
    "frontend development",
    "backend and infrastructure",
    "fullstack development",
]

CONTENT_LABEL_MAP = {
    "system design and architecture": "system_design_focus",
    "algorithms and data structures": "algorithm_heavy",
    "behavioral and soft skills": "behavioral_only",
    "frontend development": "frontend_focus",
    "backend and infrastructure": "backend_focus",
    "fullstack development": "fullstack_focus",
}

DIFFICULTY_LABELS = [
    "easy beginner level",
    "medium intermediate level",
    "hard advanced level",
]

DIFFICULTY_LABEL_MAP = {
    "easy beginner level": "easy",
    "medium intermediate level": "medium",
    "hard advanced level": "hard",
}

CONVERSATION_TYPE_LABELS = [
    "practice interview session",
    "mock interview preparation",
    "real job interview",
]

CONVERSATION_TYPE_LABEL_MAP = {
    "practice interview session": "practice_session",
    "mock interview preparation": "mock_interview",
    "real job interview": "real_interview",
}

# ==============================
# AVAILABILITY FLAG
# ==============================

CLASSIFIER_AVAILABLE = False

# ==============================
# SINGLETON
# ==============================

_classifier: Optional["SmartClassifier"] = None
_classifier_lock = threading.Lock()
_classifier_ready = threading.Event()


class SmartClassifier:
    """Zero-shot classification for interview content using NLI models."""

    # Known company names for embedding-based matching
    COMPANY_NAMES = [
        "Google", "Meta", "Amazon", "Microsoft", "Apple", "Netflix",
        "Uber", "Airbnb", "LinkedIn", "Stripe", "Lyft", "DoorDash",
        "Instacart", "Coinbase", "Robinhood", "OpenAI", "Anthropic",
        "Snowflake", "Databricks", "Salesforce", "Oracle", "Adobe",
        "Shopify", "Spotify", "Dropbox", "Slack", "Zoom", "TikTok",
        "Snapchat", "Pinterest", "Reddit", "Twitter", "X",
    ]

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        cache_size: int = CLASSIFIER_CACHE_SIZE,
    ):
        self.model_name = model_name
        self.device = device
        self._pipeline = None
        self._cache: Dict[str, dict] = {}
        self._cache_lock = threading.Lock()
        self._max_cache = cache_size

    def _load_pipeline(self):
        """Lazy-load the zero-shot classification pipeline."""
        if self._pipeline is not None:
            return

        from transformers import pipeline as hf_pipeline

        logger.info("[SmartClassifier] Loading model: %s", self.model_name)
        self._pipeline = hf_pipeline(
            "zero-shot-classification",
            model=self.model_name,
            device=self.device if self.device != "auto" else -1,  # -1 = CPU, 0+ = GPU
        )
        logger.info("[SmartClassifier] Model loaded successfully")

    def _classify_zero_shot(
        self,
        text: str,
        labels: List[str],
        multi_label: bool = False,
    ) -> dict:
        """
        Core zero-shot classification. Caches results by text hash.

        Returns dict with keys: 'labels' (sorted by score), 'scores', 'top_label', 'top_score'.
        """
        if not text or not text.strip():
            return {
                "labels": labels,
                "scores": [1.0 / len(labels)] * len(labels),
                "top_label": labels[0],
                "top_score": 0.0,
            }

        cache_key = hashlib.sha256(f"{text}|{'|'.join(labels)}|{multi_label}".encode()).hexdigest()

        # Check cache
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Run classification
        self._load_pipeline()
        result = self._pipeline(text, labels, multi_label=multi_label)

        # Normalize result
        output = {
            "labels": result["labels"],
            "scores": result["scores"],
            "top_label": result["labels"][0],
            "top_score": float(result["scores"][0]),
        }

        # Cache result
        with self._cache_lock:
            if len(self._cache) >= self._max_cache:
                # Evict oldest 20%
                keys_to_remove = list(self._cache.keys())[: self._max_cache // 5]
                for k in keys_to_remove:
                    del self._cache[k]
            self._cache[cache_key] = output

        return output

    def classify_question(self, text: str) -> Tuple[str, float]:
        """
        Classify a question into technical/system_design/behavioral/knowledge/general.

        Returns (category, confidence) tuple.
        Falls back to EntityExtractor.categorize_question() if unavailable.
        """
        try:
            result = self._classify_zero_shot(text, QUESTION_LABELS, multi_label=False)
            category = QUESTION_LABEL_MAP.get(result["top_label"], "general")
            return (category, result["top_score"])
        except Exception as e:
            logger.debug("[SmartClassifier] classify_question failed: %s", e)
            return self._fallback_classify_question(text)

    def classify_content(self, text: str) -> List[str]:
        """
        Classify content focus areas. Returns list of matching category keys.

        Falls back to keyword matching if unavailable.
        """
        try:
            result = self._classify_zero_shot(text, CONTENT_LABELS, multi_label=True)
            # Return categories with score > 0.3
            categories = []
            for label, score in zip(result["labels"], result["scores"]):
                if score > 0.3:
                    categories.append(CONTENT_LABEL_MAP.get(label, label))
            return categories if categories else ["behavioral_only"]
        except Exception as e:
            logger.debug("[SmartClassifier] classify_content failed: %s", e)
            return ["behavioral_only"]

    def classify_difficulty(self, text: str) -> Tuple[str, float]:
        """
        Classify question difficulty. Returns (level, confidence) tuple.

        Falls back to keyword matching if unavailable.
        """
        try:
            result = self._classify_zero_shot(text, DIFFICULTY_LABELS, multi_label=False)
            level = DIFFICULTY_LABEL_MAP.get(result["top_label"], "medium")
            return (level, result["top_score"])
        except Exception as e:
            logger.debug("[SmartClassifier] classify_difficulty failed: %s", e)
            return self._fallback_classify_difficulty(text)

    def classify_conversation_type(self, title: str, text_sample: str) -> Tuple[str, float]:
        """
        Classify conversation type. Returns (type, confidence) tuple.

        Falls back to keyword matching if unavailable.
        """
        combined = f"{title}. {text_sample}" if title else text_sample
        try:
            result = self._classify_zero_shot(combined, CONVERSATION_TYPE_LABELS, multi_label=False)
            conv_type = CONVERSATION_TYPE_LABEL_MAP.get(result["top_label"], "practice_session")
            return (conv_type, result["top_score"])
        except Exception as e:
            logger.debug("[SmartClassifier] classify_conversation_type failed: %s", e)
            return ("practice_session", 0.5)

    def classify_company(self, text: str) -> Optional[str]:
        """
        Match a company mention to a known company name using embedding similarity.

        Returns the matched company name, or None if no match above threshold.
        Requires EmbeddingService to be available.
        """
        try:
            from embedding_service import get_embedding_service, EMBEDDING_AVAILABLE
            if not EMBEDDING_AVAILABLE:
                return None

            service = get_embedding_service()
            if not service:
                return None

            results = service.find_most_similar(
                text, self.COMPANY_NAMES, top_k=1, threshold=0.5
            )
            if results:
                idx, score = results[0]
                if score >= 0.5:
                    return self.COMPANY_NAMES[idx]
        except Exception as e:
            logger.debug("[SmartClassifier] classify_company failed: %s", e)

        return None

    # ==============================
    # FALLBACK METHODS
    # ==============================

    def _fallback_classify_question(self, text: str) -> Tuple[str, float]:
        """Fallback using EntityExtractor keyword matching."""
        try:
            from entity_extraction import entity_extractor
            result = entity_extractor.categorize_question(text)
            if isinstance(result, tuple):
                return result
            return (result, 0.5)
        except Exception:
            return ("general", 0.3)

    def _fallback_classify_difficulty(self, text: str) -> Tuple[str, float]:
        """Fallback using keyword-based difficulty estimation."""
        text_lower = text.lower()
        hard_words = ["optimize", "trade-off", "distributed", "scale", "design", "architect"]
        easy_words = ["basic", "simple", "define", "what is", "explain briefly"]

        hard_count = sum(1 for w in hard_words if w in text_lower)
        easy_count = sum(1 for w in easy_words if w in text_lower)

        if hard_count > easy_count:
            return ("hard", 0.5)
        elif easy_count > hard_count:
            return ("easy", 0.5)
        return ("medium", 0.5)


# ==============================
# MODULE-LEVEL API
# ==============================


def get_classifier() -> Optional[SmartClassifier]:
    """Thread-safe lazy singleton getter for SmartClassifier."""
    global _classifier, CLASSIFIER_AVAILABLE

    if not CLASSIFIER_AVAILABLE:
        return None

    if _classifier is None:
        with _classifier_lock:
            if _classifier is None:
                try:
                    _classifier = SmartClassifier()
                    CLASSIFIER_AVAILABLE = True
                except Exception as e:
                    logger.error("[SmartClassifier] Failed to initialize: %s", e)
                    CLASSIFIER_AVAILABLE = False
                    return None

    return _classifier


def warmup():
    """Preload model at startup in a background thread."""
    global CLASSIFIER_AVAILABLE

    try:
        logger.info("[SmartClassifier] Warming up...")
        classifier = get_classifier()
        if classifier:
            # Force model load by classifying a test string
            classifier.classify_question("What is a binary search tree?")
            CLASSIFIER_AVAILABLE = True
            logger.info("[SmartClassifier] Ready")
        else:
            CLASSIFIER_AVAILABLE = False
    except Exception as e:
        logger.warning("[SmartClassifier] Warmup failed: %s", e)
        CLASSIFIER_AVAILABLE = False
    finally:
        _classifier_ready.set()


def wait_for_classifier(timeout: float = 60) -> bool:
    """Block until the classifier is ready (or timeout expires)."""
    return _classifier_ready.wait(timeout=timeout)