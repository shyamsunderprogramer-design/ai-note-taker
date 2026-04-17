"""
Graph Loader — Loads parsed Q&A pairs into the Cognitive Graph (Neo4j).

Uses existing CognitiveGraph methods to create Question, Answer, Topic, and
Skill nodes. Falls back to JSON cache when Neo4j is unavailable.
"""

import json
import hashlib
import time
import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("agents.ingestion.graph_loader")

# Cache directory for when Neo4j is unavailable
CACHE_DIR = os.path.join("platform", "data", "ingestion")
CACHE_FILE = os.path.join(CACHE_DIR, "graph_cache.json")


@dataclass
class LoadStats:
    """Statistics from a graph loading operation."""
    total_pairs: int = 0
    loaded: int = 0
    skipped_duplicates: int = 0
    errors: int = 0
    nodes_created: int = 0
    cached: int = 0  # Stored in JSON cache instead of Neo4j
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_pairs": self.total_pairs,
            "loaded": self.loaded,
            "skipped_duplicates": self.skipped_duplicates,
            "errors": self.errors,
            "nodes_created": self.nodes_created,
            "cached": self.cached,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


class GraphLoader:
    """Load parsed Q&A pairs into the Cognitive Graph."""

    def __init__(self):
        self._cognitive_graph = None
        self._entity_extractor = None
        self._has_neo4j = None
        self._loaded_hashes: set = set()
        self._cache: List[Dict] = []

    @property
    def cognitive_graph(self):
        """Lazy-load CognitiveGraph singleton."""
        if self._cognitive_graph is None:
            try:
                from ai.cognitive_graph import cognitive_graph
                self._cognitive_graph = cognitive_graph
            except ImportError:
                try:
                    from modules.ai.cognitive_graph import cognitive_graph
                    self._cognitive_graph = cognitive_graph
                except ImportError:
                    from backend.modules.ai.cognitive_graph import cognitive_graph
                    self._cognitive_graph = cognitive_graph
        return self._cognitive_graph

    @property
    def entity_extractor(self):
        """Lazy-load EntityExtractor singleton."""
        if self._entity_extractor is None:
            try:
                from ai.entity_extraction import entity_extractor
                self._entity_extractor = entity_extractor
            except ImportError:
                try:
                    from modules.ai.entity_extraction import entity_extractor
                    self._entity_extractor = entity_extractor
                except ImportError:
                    from backend.modules.ai.entity_extraction import entity_extractor
                    self._entity_extractor = entity_extractor
        return self._entity_extractor

    def _check_neo4j(self) -> bool:
        """Check if Neo4j is available."""
        if self._has_neo4j is None:
            try:
                cg = self.cognitive_graph
                self._has_neo4j = bool(cg and hasattr(cg, 'driver') and cg.driver)
            except Exception:
                self._has_neo4j = False
        return self._has_neo4j

    def load_qa_pairs(self, qa_pairs: list) -> LoadStats:
        """Load Q&A pairs into the cognitive graph.

        For each pair:
        1. Check for duplicates via MD5 hash
        2. Extract entities (companies, topics, skills)
        3. Create Question + Answer nodes
        4. Link to Topic and Skill nodes

        Falls back to JSON cache when Neo4j is unavailable.

        Args:
            qa_pairs: List of ParsedQA objects from markdown_parser

        Returns:
            LoadStats with loading statistics
        """
        from agents.ingestion.markdown_parser import ParsedQA

        stats = LoadStats(total_pairs=len(qa_pairs))
        start_time = time.time()
        has_neo4j = self._check_neo4j()

        if has_neo4j:
            logger.info("[GraphLoader] Neo4j available — loading directly")
        else:
            logger.warning("[GraphLoader] Neo4j unavailable — caching to JSON")

        for qa in qa_pairs:
            if not isinstance(qa, ParsedQA):
                stats.errors += 1
                continue

            # Dedup check
            q_hash = self._qa_to_hash(qa.question)
            if q_hash in self._loaded_hashes:
                stats.skipped_duplicates += 1
                continue
            self._loaded_hashes.add(q_hash)

            try:
                # Extract entities from the Q&A pair
                entities = self._extract_entities(qa)

                if has_neo4j:
                    loaded = self._load_to_neo4j(qa, entities)
                    if loaded:
                        stats.loaded += 1
                        stats.nodes_created += 3  # Question + Answer + at least 1 Topic
                    else:
                        stats.errors += 1
                else:
                    # Cache for later
                    self._cache_qa(qa, entities)
                    stats.cached += 1

            except Exception as e:
                logger.error(f"[GraphLoader] Error loading Q#{qa.number} from {qa.category}: {e}")
                stats.errors += 1

        # Save cache if needed
        if not has_neo4j and self._cache:
            self._save_cache()

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"[GraphLoader] Done: {stats.loaded} loaded, "
            f"{stats.cached} cached, {stats.skipped_duplicates} dupes, "
            f"{stats.errors} errors in {stats.elapsed_seconds:.1f}s"
        )
        return stats

    def batch_load(self, qa_pairs: list, batch_size: int = 20) -> LoadStats:
        """Load Q&A pairs in batches to avoid memory issues.

        Args:
            qa_pairs: List of ParsedQA objects
            batch_size: Number of Q&A pairs per batch

        Returns:
            Combined LoadStats across all batches
        """
        combined = LoadStats()
        start_time = time.time()

        for i in range(0, len(qa_pairs), batch_size):
            batch = qa_pairs[i:i + batch_size]
            batch_stats = self.load_qa_pairs(batch)

            combined.total_pairs += batch_stats.total_pairs
            combined.loaded += batch_stats.loaded
            combined.skipped_duplicates += batch_stats.skipped_duplicates
            combined.errors += batch_stats.errors
            combined.nodes_created += batch_stats.nodes_created
            combined.cached += batch_stats.cached

            if i + batch_size < len(qa_pairs) and i % (batch_size * 5) == 0:
                logger.info(f"[GraphLoader] Progress: {i + batch_size}/{len(qa_pairs)} pairs processed")

        combined.elapsed_seconds = time.time() - start_time
        return combined

    def _load_to_neo4j(self, qa, entities: Dict) -> bool:
        """Load a single Q&A pair into Neo4j.

        Args:
            qa: ParsedQA object
            entities: Extracted entities dict

        Returns:
            True if successfully loaded
        """
        cg = self.cognitive_graph
        if not cg or not cg.driver:
            return False

        try:
            # Create Question + Answer nodes
            question_id = cg.add_question_answer(
                question_text=qa.question,
                answer_text=qa.answer,
                category=qa.category,
                difficulty=qa.difficulty,
                company=None,
            )

            if not question_id:
                return False

            # Link Topic nodes
            topics = entities.get("topics", [])
            if topics:
                try:
                    cg.add_topics_to_question(question_id, topics[:5])
                except Exception as e:
                    logger.debug(f"[GraphLoader] Topic linking failed: {e}")

            # Link Skill nodes
            skills = entities.get("skills", [])
            if skills:
                try:
                    # Use the answer ID from the last created answer
                    # (add_question_answer creates it internally)
                    skill_names = skills[:5]
                    # Note: add_skills_to_answer needs an answer_id
                    # We'll link skills via topics as a workaround
                    cg.add_topics_to_question(question_id, skill_names[:3])
                except Exception as e:
                    logger.debug(f"[GraphLoader] Skill linking failed: {e}")

            return True

        except Exception as e:
            logger.error(f"[GraphLoader] Neo4j load error: {e}")
            return False

    def _extract_entities(self, qa) -> Dict:
        """Extract entities from a Q&A pair using the EntityExtractor."""
        try:
            extractor = self.entity_extractor
            if extractor:
                combined_text = f"{qa.question} {qa.answer}"
                return extractor.extract_all(combined_text)
        except Exception as e:
            logger.debug(f"[GraphLoader] Entity extraction failed: {e}")
        return {}

    def _cache_qa(self, qa, entities: Dict) -> None:
        """Cache a Q&A pair for later loading into Neo4j."""
        self._cache.append({
            "question": qa.question,
            "answer": qa.answer,
            "category": qa.category,
            "difficulty": qa.difficulty,
            "number": qa.number,
            "source_file": qa.source_file,
            "entities": {
                "topics": entities.get("topics", []),
                "skills": entities.get("skills", []),
                "companies": entities.get("companies", []),
            },
            "hash": self._qa_to_hash(qa.question),
        })

    def _save_cache(self) -> None:
        """Save cached Q&A pairs to a JSON file for later import."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        try:
            # Merge with existing cache
            existing = []
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, IOError):
                    existing = []

            existing_hashes = {item.get("hash") for item in existing}
            new_items = [item for item in self._cache if item["hash"] not in existing_hashes]
            existing.extend(new_items)

            with open(CACHE_FILE, "w") as f:
                json.dump(existing, f, indent=2)

            logger.info(f"[GraphLoader] Saved {len(new_items)} Q&A pairs to cache ({CACHE_FILE})")
        except Exception as e:
            logger.error(f"[GraphLoader] Cache save failed: {e}")

    def load_from_cache(self) -> LoadStats:
        """Load Q&A pairs from the JSON cache into Neo4j.

        Call this after Neo4j becomes available to import previously cached data.

        Returns:
            LoadStats with loading statistics
        """
        if not os.path.exists(CACHE_FILE):
            logger.info("[GraphLoader] No cache file found")
            return LoadStats()

        try:
            with open(CACHE_FILE, "r") as f:
                cached_items = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"[GraphLoader] Cache read error: {e}")
            return LoadStats()

        if not cached_items:
            return LoadStats()

        logger.info(f"[GraphLoader] Loading {len(cached_items)} cached Q&A pairs")

        # Convert cache items to ParsedQA-like objects and load them
        from agents.ingestion.markdown_parser import ParsedQA

        qa_pairs = []
        for item in cached_items:
            qa = ParsedQA(
                question=item["question"],
                answer=item["answer"],
                number=item.get("number", 0),
                category=item.get("category", ""),
                difficulty=item.get("difficulty", "beginner"),
                source_file=item.get("source_file", "cache"),
            )
            qa_pairs.append(qa)

        stats = self.load_qa_pairs(qa_pairs)

        # If successful, clear the cache
        if stats.loaded > 0 and stats.errors == 0:
            try:
                os.remove(CACHE_FILE)
                logger.info("[GraphLoader] Cache cleared after successful import")
            except Exception:
                pass  # nosec B110

        return stats

    @staticmethod
    def _qa_to_hash(question: str) -> str:
        """Generate hash of a normalized question for deduplication (non-cryptographic)."""
        normalized = " ".join(question.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()  # nosec B324 — used for deduplication, not security

    def get_loaded_count(self) -> int:
        """Get the total number of Q&A pairs loaded in this session."""
        return len(self._loaded_hashes)